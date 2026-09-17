"""The orchestrator: Python control flow that drives one job through the pipeline.

This module is where the architecture's central claim is actually enforced:

    AI DECIDES. PYTHON CONTROLS. PLAYWRIGHT EXECUTES. VERIFICATION PROVES IT.

Every state change goes through `state.machine.assert_transition`, so an illegal
move raises rather than silently corrupting the job. The LLM is called from
exactly one place - the POLICY_CHECK step - and its answer is a value, not a
command: `DECISION_ROUTES` decides where the job goes next, and the decision has
already passed through the Python guards by the time it gets here.

The agent never chooses to execute. The routing table does.

STATE IS NOT DECISION. `job.state` says where the job is; `job.decision` says what
was concluded. A job in EXECUTING carrying APPROVE and a job in EXECUTING carrying
REJECT are in the same state with different decisions, and that is the point.

WORKFLOW-NEUTRAL BY CONSTRUCTION. Nothing below mentions leave or payroll. The
five things that differ per workflow - definition, record type, policy key, policy
gates and record loader - come from `workflows.registry`, so adding a third
workflow does not touch this file. That is the test of whether this is a platform
or a demo with two hardcoded branches.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from itertools import count
from typing import Optional

import repository
from agent import decide_record
from execution import ActionNotAutoExecutable, action_spec_for, execute_decision
from models.agent import AgentDecision
from models.common import AmbiguityType, DecisionType, WorkflowType
from models.execution import VerificationStatus
from models.job import AutomationJob, HumanDecision, StateTransition
from mockhr import reset_all as reset_hr_system
from state.machine import JobState, assert_transition, next_state_for_decision
from workflows.registry import BusinessRecord, WorkflowBinding, binding_for

logger = logging.getLogger(__name__)

#: One browser at a time. The executor drives a real Chromium instance against a
#: single shared mock HR system, so concurrent runs would interleave clicks and
#: make verification meaningless.
_EXECUTION_LOCK = threading.Lock()


class JobNotFound(KeyError):
    """No job with that id."""


class RecordNotFound(KeyError):
    """No such record exists in the HR system, so no job can be started for it."""


class JobNotInReview(RuntimeError):
    """A human determination was submitted for a job that is not awaiting one."""


class JobStore:
    """In-memory job registry. Restarting the process clears it, by design."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, AutomationJob] = {}
        self._counter = count(1)

    def new_job_id(self) -> str:
        return f"JOB-{next(self._counter):04d}"

    def put(self, job: AutomationJob) -> AutomationJob:
        with self._lock:
            self._jobs[job.job_id] = job
            return job

    def get(self, job_id: str) -> AutomationJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFound(job_id)
            return job

    def all(self) -> list[AutomationJob]:
        """Every job, newest first."""
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def reset(self) -> None:
        with self._lock:
            self._jobs = {}
            self._counter = count(1)


jobs = JobStore()


def _move(job: AutomationJob, target: JobState, note: Optional[str] = None) -> None:
    """Move a job to a new state, checking legality and recording the transition."""
    assert_transition(job.state, target)
    now = datetime.now(timezone.utc)
    job.state_history.append(
        StateTransition(from_state=job.state, to_state=target, at=now, note=note)
    )
    job.state = target
    job.updated_at = now


def _fail(job: AutomationJob, message: str) -> AutomationJob:
    job.error = message
    _move(job, JobState.FAILED, message)
    return jobs.put(job)


def _load_record(binding: WorkflowBinding, record_id: str) -> BusinessRecord:
    """Read the record from the mock HR system - its live state, not the seed file.

    This matters: a record confirmed earlier in the demo must present as confirmed
    here, so a second run on it is correctly refused rather than silently redone.
    """
    return binding.load_record(record_id)


def _execute_and_verify(
    job: AutomationJob,
    decision: DecisionType,
    comment: Optional[str],
    executed_by: str,
    human_authorised: bool,
) -> AutomationJob:
    """Run EXECUTING -> VERIFYING -> COMPLETED/FAILED for an already-decided job."""
    binding = binding_for(job.workflow)

    _move(job, JobState.EXECUTING, f"Executing {decision.value}")
    jobs.put(job)

    try:
        with _EXECUTION_LOCK:
            result = execute_decision(
                record=job.record,
                decision=decision,
                workflow=binding.definition,
                comment=comment,
                executed_by=executed_by,
                human_authorised=human_authorised,
            )
    except ActionNotAutoExecutable as exc:
        return _fail(job, str(exc))

    job.execution = result
    job.updated_at = datetime.now(timezone.utc)

    if not result.success:
        # The clicks themselves failed; there is nothing to verify.
        return _fail(job, result.error or "Execution failed before any action was taken.")

    _move(job, JobState.VERIFYING, "Independently re-reading the record status")
    jobs.put(job)

    if result.verification_status is VerificationStatus.VERIFIED:
        _move(
            job,
            JobState.COMPLETED,
            f"Verified: {result.status_before} -> {result.status_after}",
        )
        # Reflect the real post-action record back onto the job.
        job.record = _load_record(binding, job.record.record_id)
        return jobs.put(job)

    # Every step ran, but the record did not end up where it should have. This is
    # deliberately NOT reported as a success - see execution/verification.py.
    return _fail(
        job,
        result.error
        or (
            "Execution completed but verification did not observe the expected status. "
            "The run is not being reported as successful."
        ),
    )


def start_job(
    workflow: WorkflowType, record_id: str, run_execution: bool = True
) -> AutomationJob:
    """Take one record from START to a terminal or awaiting-human state.

    `run_execution=False` stops after POLICY_CHECK. Useful for showing the decision
    in the UI without touching the HR system - and for tests that must not launch
    a browser.
    """
    binding = binding_for(workflow)

    try:
        record = _load_record(binding, record_id)
    except KeyError as exc:
        raise RecordNotFound(record_id) from exc

    now = datetime.now(timezone.utc)
    job = AutomationJob(
        job_id=jobs.new_job_id(),
        workflow=workflow,
        state=JobState.START,
        record=record,
        created_at=now,
        updated_at=now,
    )
    jobs.put(job)

    # --- LOADING ------------------------------------------------------------
    _move(job, JobState.LOADING, f"Loaded {record_id} from the HR system")
    jobs.put(job)

    # --- VALIDATING ---------------------------------------------------------
    # Structural readability only. Business completeness is a POLICY_CHECK gate,
    # so that an incomplete record still receives a full, explained decision
    # rather than a bare state jump the UI cannot account for.
    _move(job, JobState.VALIDATING, "Record loaded and structurally valid")
    jobs.put(job)

    # --- ANALYZING ----------------------------------------------------------
    _move(job, JobState.ANALYZING, "Extracting the decision-relevant fields")
    jobs.put(job)

    # --- POLICY_CHECK -------------------------------------------------------
    _move(job, JobState.POLICY_CHECK, "Evaluating the configured policy")
    jobs.put(job)

    policy = repository.get_policy(binding.policy_key)
    decision: AgentDecision = decide_record(job.record, policy, binding)
    job.decision = decision
    job.updated_at = datetime.now(timezone.utc)
    jobs.put(job)

    # Routing is a lookup table, not a model output. See state.machine.
    target = next_state_for_decision(decision.decision)

    if target is JobState.HUMAN_REVIEW:
        _move(job, JobState.HUMAN_REVIEW, decision.reason)
        return jobs.put(job)

    # The workflow may still forbid unattended execution of this action even when
    # the decision itself is APPROVE/REJECT - e.g. leave rejection or payroll hold,
    # neither of which was ever observed being performed in Dataset B.
    spec = action_spec_for(binding.definition, decision.decision)
    if spec is None or not spec.auto_executable:
        rationale = spec.rationale if spec else "No execution action is defined."
        job.decision = decision.model_copy(
            update={
                "decision": DecisionType.REVIEW,
                "human_review_required": True,
                "ambiguity_type": AmbiguityType.ACTION_NOT_AUTO_EXECUTABLE,
                "reason": f"{decision.reason} [guard override] {rationale}",
            }
        )
        _move(job, JobState.HUMAN_REVIEW, rationale)
        return jobs.put(job)

    if not run_execution:
        return jobs.put(job)

    return _execute_and_verify(
        job,
        decision=decision.decision,
        comment=f"Automated decision ({decision.policy_version}): {decision.reason}"[:500],
        executed_by="agent",
        human_authorised=False,
    )


def start_leave_job(record_id: str, run_execution: bool = True) -> AutomationJob:
    """Workflow-specific alias for `start_job`, kept for readability."""
    return start_job(WorkflowType.LEAVE_APPROVAL, record_id, run_execution)


def start_payroll_job(record_id: str, run_execution: bool = True) -> AutomationJob:
    """Workflow-specific alias for `start_job`, kept for readability."""
    return start_job(WorkflowType.PAYROLL_CONFIRMATION, record_id, run_execution)


def submit_human_decision(
    job_id: str,
    decision: DecisionType,
    operator: str,
    note: str,
    run_execution: bool = True,
) -> AutomationJob:
    """Record an operator's determination and, optionally, carry it out.

    The human's determination is stored alongside the agent's, never on top of it.
    Execution then runs with `human_authorised=True`, which is the ONLY way an
    action the policy forbids unattended (rejection) ever reaches the browser.
    """
    job = jobs.get(job_id)
    if job.state is not JobState.HUMAN_REVIEW:
        raise JobNotInReview(
            f"{job_id} is {job.state.value}; only jobs in HUMAN_REVIEW accept a "
            "human determination."
        )

    job.human_decision = HumanDecision(
        decision=decision,
        operator=operator,
        note=note,
        at=datetime.now(timezone.utc),
    )
    job.updated_at = datetime.now(timezone.utc)
    jobs.put(job)

    if not run_execution:
        _move(job, JobState.COMPLETED, f"Resolved by {operator} without execution")
        return jobs.put(job)

    return _execute_and_verify(
        job,
        decision=decision,
        comment=f"{operator}: {note}"[:500],
        executed_by=f"human:{operator}",
        human_authorised=True,
    )


def reset_demo() -> dict[str, int]:
    """Restore every mock HR queue and clear all jobs, so the demo can be re-run."""
    reset_hr_system()
    jobs.reset()
    from mockhr import leave_store, payroll_store

    return {
        "leave_records_restored": len(leave_store.all()),
        "payroll_records_restored": len(payroll_store.all()),
        "jobs_cleared": 0,
    }
