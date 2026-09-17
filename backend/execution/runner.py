"""Turns a decided action into a browser run and a structured ExecutionResult.

NO LLM IN THIS FILE. The decision arrives already made; this module performs it,
verifies it independently, and records what happened step by step.

The step sequence mirrors the human action sequence confirmed by screenshot in
`phase2_dataset_b/visual_audit.md` for segment
`ses_20260701-180923-NEELA9BAF::seg013`:

    open the queue -> locate the record -> open its detail panel -> read the
    fields -> enter a comment -> click the decided control -> re-read the status

Two fields of `ExecutionResult` are kept rigorously distinct:

    success              did every step run without throwing?
    verification_status  did the record actually end up in the expected state?

A run with `success=True, verification_status=FAILED` is a real and important
outcome - the clicks worked, the record did not change - and it is reported as a
failure, not as a success.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from models.common import DecisionType, WorkflowType
from models.execution import (
    ExecutionAction,
    ExecutionResult,
    ExecutionStep,
    VerificationStatus,
)
from models.leave import LeaveRequest
from workflows.base import ExecutionActionSpec, WorkflowDefinition

from .playwright_executor import ExecutionError, LeaveApprovalExecutor
from .verification import verify_record_status

logger = logging.getLogger(__name__)


class ActionNotAutoExecutable(RuntimeError):
    """The workflow forbids performing this action without a human."""


def action_spec_for(
    workflow: WorkflowDefinition, decision: DecisionType
) -> Optional[ExecutionActionSpec]:
    """The workflow's spec for turning this decision into a UI action."""
    for spec in workflow.execution_actions:
        if spec.decision is decision:
            return spec
    return None


def _step(name: str, detail: Optional[str] = None) -> ExecutionStep:
    return ExecutionStep(
        name=name, completed=True, detail=detail, at=datetime.now(timezone.utc)
    )


def execute_leave_decision(
    record: LeaveRequest,
    decision: DecisionType,
    workflow: WorkflowDefinition,
    comment: Optional[str] = None,
    executed_by: str = "agent",
    human_authorised: bool = False,
    headless: Optional[bool] = None,
) -> ExecutionResult:
    """Perform a decided leave action in the mock HR system and verify the result.

    `human_authorised=True` is how the human-review path executes an action the
    policy is not allowed to take unattended. It relaxes the `auto_executable`
    gate and nothing else - the same clicks happen, the same independent
    verification runs, and `executed_by` records who authorised it.
    """
    spec = action_spec_for(workflow, decision)
    if spec is None:
        raise ActionNotAutoExecutable(
            f"{workflow.name} defines no execution action for decision {decision.value}."
        )
    if not spec.auto_executable and not human_authorised:
        raise ActionNotAutoExecutable(
            f"{spec.action.value} is not auto-executable in this workflow. {spec.rationale}"
        )

    started = datetime.now(timezone.utc)
    steps: list[ExecutionStep] = []
    status_before: Optional[str] = None
    status_after: Optional[str] = None
    verification = VerificationStatus.NOT_ATTEMPTED
    error: Optional[str] = None
    success = False

    # `headless=None` means "use the environment default" - see the executor.

    try:
        with LeaveApprovalExecutor(headless=headless) as executor:
            executor.open_queue()
            steps.append(_step("Open leave application queue", executor.base_url))

            executor.open_request(record.record_id)
            steps.append(
                _step("Locate and open the record", f"Opened {record.record_id}")
            )

            details = executor.get_request_details()
            status_before = details["status"]
            steps.append(
                _step(
                    "Read the record fields",
                    ", ".join(f"{k}={v}" for k, v in details.items() if v),
                )
            )

            if comment:
                steps.append(_step("Enter approval comment", comment))

            if decision is DecisionType.APPROVE:
                executor.approve_request(comment)
            elif decision is DecisionType.REJECT:
                executor.reject_request(comment)
            else:
                raise ActionNotAutoExecutable(
                    f"Decision {decision.value} is not an executable action."
                )
            steps.append(
                _step(
                    f"Click {spec.ui_target_label} and submit",
                    "Located by [data-testid], not by position.",
                )
            )

            # Every step ran. Whether it WORKED is a separate question, asked next.
            success = True

            outcome = verify_record_status(
                executor, record.record_id, workflow, decision
            )
            verification = outcome.status
            status_after = outcome.observed_status
            steps.append(
                ExecutionStep(
                    name="Independently re-read the record status",
                    completed=outcome.verified,
                    detail=outcome.detail,
                    error=None if outcome.verified else outcome.detail,
                    at=datetime.now(timezone.utc),
                )
            )
            if not outcome.verified:
                error = outcome.detail

    except ExecutionError as exc:
        error = str(exc)
        steps.append(
            ExecutionStep(
                name="Browser execution",
                completed=False,
                error=error,
                at=datetime.now(timezone.utc),
            )
        )
    except ActionNotAutoExecutable:
        raise
    except Exception as exc:  # noqa: BLE001 - anything else is still a failed run
        error = f"{type(exc).__name__}: {exc}"
        logger.exception("Unexpected failure executing %s", record.record_id)
        steps.append(
            ExecutionStep(
                name="Browser execution",
                completed=False,
                error=error,
                at=datetime.now(timezone.utc),
            )
        )

    finished = datetime.now(timezone.utc)
    return ExecutionResult(
        action=spec.action,
        workflow=WorkflowType.LEAVE_APPROVAL,
        record_id=record.record_id,
        success=success,
        steps_completed=steps,
        verification_status=verification,
        status_before=status_before,
        status_after=status_after,
        error=error,
        started_at=started,
        finished_at=finished,
        # Measured, never estimated.
        duration_seconds=round((finished - started).total_seconds(), 3),
        executed_by=executed_by,
    )


#: Re-exported so callers do not need to know which module defines it.
__all__ = [
    "ActionNotAutoExecutable",
    "ExecutionAction",
    "action_spec_for",
    "execute_leave_decision",
]
