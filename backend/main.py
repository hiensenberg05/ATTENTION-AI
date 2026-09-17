"""FastAPI application for the Back-Office Automation Agent prototype.

FOUNDATION STAGE ONLY. These endpoints are read-only data access so the later
agent, executor and React layers have something stable to build against. There is
deliberately no agent endpoint, no execution endpoint and no LLM call here.

Run from inside `backend/`:

    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

import orchestrator
import repository
from agent import agent_health
from mockhr import router as mockhr_router
from mockhr import leave_store, payroll_store
from models.common import DecisionType, LeaveStatus, PayrollStatus, WorkflowType
from models.job import AutomationJob
from models.payroll import PayrollItem
from models.leave import LeaveRequest
from workflows.base import WorkflowDefinition

app = FastAPI(
    title="Back-Office Automation Agent",
    version="0.3.0",
    description=(
        "Bounded workflow-execution prototype built from the Phase 1/2 analysis of "
        "desktop operation logs. An LLM evaluates an explicit policy and produces a "
        "structured decision; Python routes the job through a state machine; "
        "Playwright performs the decided action in a mock HR system; and an "
        "independent re-read verifies that the record actually changed."
    ),
)

# The React dashboard is a later stage and will run on its own dev-server origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# The mock internal HR application. It shares this process for convenience, but it
# is a separate application: server-rendered HTML with its own mutable store, which
# the executor reaches over HTTP through a real browser like any external system.
app.include_router(mockhr_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, object]:
    """Liveness check plus a count of what loaded, so a bad data file is obvious."""
    return {
        "status": "ok",
        "stage": "agent+execution",
        "agent": agent_health(),
        "workflows_defined": len(repository.get_workflows()),
        "leave_requests_loaded": len(leave_store.all()),
        "payroll_items_loaded": len(payroll_store.all()),
    }


@app.get("/api/workflows", response_model=list[WorkflowDefinition], tags=["workflows"])
def list_workflows() -> list[WorkflowDefinition]:
    """Every defined workflow, including its Phase 2 evidence and caveats.

    Only Leave Approval is defined. Payroll Confirmation exists as an enum member
    with demo data and a draft policy, but has no definition yet.
    """
    return list(repository.get_workflows())


@app.get(
    "/api/workflows/{workflow}",
    response_model=WorkflowDefinition,
    tags=["workflows"],
)
def get_workflow(workflow: WorkflowType) -> WorkflowDefinition:
    """One workflow definition by type."""
    definition = repository.get_workflow(workflow)
    if definition is None:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow {workflow.value} is declared but not defined yet.",
        )
    return definition


@app.get("/api/leave-requests", response_model=list[LeaveRequest], tags=["leave"])
def list_leave_requests(
    status: Optional[LeaveStatus] = Query(
        default=None, description="Filter by status, e.g. 申請中"
    ),
) -> list[LeaveRequest]:
    """The leave-request queue as it stands in the mock HR system RIGHT NOW.

    Served from the live store rather than the seed file, so a record approved by
    a run a moment ago presents as approved here. A console that showed the seed
    values would be quietly lying about the system it claims to be driving.
    """
    records = leave_store.all()
    if status is not None:
        records = [r for r in records if r.status is status]
    return records


@app.get(
    "/api/leave-requests/{record_id}",
    response_model=LeaveRequest,
    tags=["leave"],
)
def get_leave_request(record_id: str) -> LeaveRequest:
    """One leave request by its 管理ID, as it stands in the mock HR system now."""
    try:
        return leave_store.get(record_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No leave request {record_id!r}")


@app.get("/api/payroll-items", response_model=list[PayrollItem], tags=["payroll"])
def list_payroll_items(
    status: Optional[PayrollStatus] = Query(
        default=None, description="Filter by status, e.g. 未処理"
    ),
) -> list[PayrollItem]:
    """The payroll/expense queue as it stands in the mock HR system RIGHT NOW."""
    records = payroll_store.all()
    if status is not None:
        records = [r for r in records if r.status is status]
    return records


@app.get(
    "/api/payroll-items/{record_id}", response_model=PayrollItem, tags=["payroll"]
)
def get_payroll_item(record_id: str) -> PayrollItem:
    """One payroll item by its 管理ID, as it stands in the mock HR system now."""
    try:
        return payroll_store.get(record_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No payroll item {record_id!r}")


@app.get("/api/policy/payroll", tags=["policy"])
def get_payroll_policy() -> dict[str, object]:
    """The explicit prototype policy for Payroll Confirmation.

    Carries the `_meta` honesty block and the section's own `production_caveat`,
    because the amount limit in particular is a demonstration value and must never
    be read as the client's approval threshold.
    """
    return {
        "_meta": repository.get_policies()["_meta"],
        "policy_key": "payroll_confirmation",
        "policy": repository.get_policy("payroll_confirmation"),
    }


@app.get("/api/policy/leave", tags=["policy"])
def get_leave_policy() -> dict[str, object]:
    """The explicit prototype policy for Leave Approval.

    Returned with the document's `_meta` block attached, so any consumer (including
    the UI) carries the statement that this is a prototype policy and was not
    learned from the operation logs.
    """
    return {
        "_meta": repository.get_policies()["_meta"],
        "policy_key": "leave_approval",
        "policy": repository.get_policy("leave_approval"),
    }


# ---------------------------------------------------------------------------
# Automation: the endpoints that actually run the pipeline.
#
# These are declared with `def`, not `async def`, on purpose. FastAPI runs a sync
# endpoint in a worker thread, which is exactly what the synchronous Playwright
# API needs - it refuses to run inside a thread that owns an asyncio event loop.
# ---------------------------------------------------------------------------


class HumanDecisionRequest(BaseModel):
    """An operator's determination on a record the agent escalated."""

    decision: DecisionType = Field(description="APPROVE or REJECT; REVIEW is rejected")
    operator: str = Field(min_length=1, description="Who is authorising this")
    note: str = Field(
        min_length=1,
        description="Mandatory audit note. A human override without a stated reason "
        "is exactly the thing this prototype is meant to prevent.",
    )
    run_execution: bool = Field(
        default=True,
        description="False records the determination without touching the HR system.",
    )


RUN_EXECUTION_QUERY = Query(
    default=True,
    description="False stops after POLICY_CHECK, so the decision can be inspected "
    "without any browser action being taken.",
)


@app.post(
    "/api/automation/{workflow}/{record_id}/start",
    response_model=AutomationJob,
    tags=["automation"],
)
def start_automation(
    workflow: WorkflowType,
    record_id: str,
    run_execution: bool = RUN_EXECUTION_QUERY,
) -> AutomationJob:
    """Run one record of any implemented workflow through the full pipeline.

    One endpoint serves every workflow, because the pipeline is the same one -
    policy gates, LLM decision, Python guards, and then either execution plus
    independent verification or a stop at human review.

    Synchronous by design: the whole run takes a couple of seconds, and a caller
    that gets the finished job back can show a real result rather than polling a
    job that may never have started. Returns the job in whatever state it reached -
    COMPLETED, FAILED, or HUMAN_REVIEW.
    """
    try:
        return orchestrator.start_job(workflow, record_id, run_execution=run_execution)
    except orchestrator.RecordNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"No {workflow.value} record {record_id!r}",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post(
    "/api/automation/leave/{record_id}/start",
    response_model=AutomationJob,
    tags=["automation"],
)
def start_leave_automation(
    record_id: str, run_execution: bool = RUN_EXECUTION_QUERY
) -> AutomationJob:
    """Leave-specific alias for the generic run endpoint. Kept so existing callers
    (and the original demo scripts) keep working."""
    return start_automation(WorkflowType.LEAVE_APPROVAL, record_id, run_execution)


@app.post(
    "/api/automation/payroll/{record_id}/start",
    response_model=AutomationJob,
    tags=["automation"],
)
def start_payroll_automation(
    record_id: str, run_execution: bool = RUN_EXECUTION_QUERY
) -> AutomationJob:
    """Payroll-specific alias for the generic run endpoint."""
    return start_automation(WorkflowType.PAYROLL_CONFIRMATION, record_id, run_execution)


@app.get(
    "/api/automation/history", response_model=list[AutomationJob], tags=["automation"]
)
def automation_history() -> list[AutomationJob]:
    """Every job this process has run, newest first.

    Declared BEFORE `/api/automation/{job_id}` so that "history" is not matched as
    a job id.

    In-memory: restarting the backend clears it. That is a deliberate prototype
    limitation, not an oversight - persisting an audit trail properly is a
    database decision, not a demo decision.
    """
    return orchestrator.jobs.all()


@app.get("/api/automation/{job_id}", response_model=AutomationJob, tags=["automation"])
def get_automation_job(job_id: str) -> AutomationJob:
    """One job, including its decision, execution result and state history."""
    try:
        return orchestrator.jobs.get(job_id)
    except orchestrator.JobNotFound:
        raise HTTPException(status_code=404, detail=f"No job {job_id!r}")


@app.post(
    "/api/automation/{job_id}/human-decision",
    response_model=AutomationJob,
    tags=["automation"],
)
def submit_human_decision(job_id: str, body: HumanDecisionRequest) -> AutomationJob:
    """Resolve a job the agent escalated, and carry out the determination.

    This is the only path by which an action the policy forbids unattended - a
    rejection - can ever reach the browser. The operator's note is mandatory and
    is written into the HR system's comment field alongside the action.
    """
    try:
        return orchestrator.submit_human_decision(
            job_id=job_id,
            decision=body.decision,
            operator=body.operator,
            note=body.note,
            run_execution=body.run_execution,
        )
    except orchestrator.JobNotFound:
        raise HTTPException(status_code=404, detail=f"No job {job_id!r}")
    except orchestrator.JobNotInReview as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/agent/health", tags=["system"])
def agent_configuration() -> dict[str, object]:
    """Whether the LLM layer is configured. Reports configuration, never the key."""
    return agent_health()


@app.post("/api/demo/reset", tags=["system"])
def reset_demo() -> dict[str, object]:
    """Restore the mock HR system to its seed state and clear the job history.

    The demo has to be re-runnable, and every run mutates records irreversibly
    (a record can only be approved once). This is the reset button.
    """
    counts = orchestrator.reset_demo()
    return {
        "status": "reset",
        "jobs": len(orchestrator.jobs.all()),
        **counts,
    }
