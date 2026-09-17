"""Independent verification that the record really changed. NO LLM IN THIS FILE.

The claim this module exists to defend:

    CLICKING A BUTTON SUCCESSFULLY IS NOT THE SAME AS THE RECORD BEING APPROVED.

So the executor's own report of "I clicked it and nothing threw" is never accepted
as proof. Verification goes back to the HR system through a different route - the
queue screen rather than the detail page the action was submitted from - re-reads
the record's status, and compares it against the label the workflow definition
says to expect.

A run is only ever reported as successful when that independent re-read observed
the expected state. If the re-read fails, is unreadable, or shows something else,
the result is VerificationStatus.FAILED and the job ends in FAILED - even though
every click "worked".

HONEST CAVEAT, carried from Phase 2: the expected post-action labels (承認済み /
差戻し) were NEVER observed in Dataset B. No approved or returned leave record was
captured in any inspected segment; only the button labels were. The expected
labels therefore come from `WorkflowDefinition.verification`, are flagged there as
a prototype assumption, and are configurable rather than hardcoded here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from models.common import DecisionType
from models.execution import VerificationStatus
from workflows.base import WorkflowDefinition

from .playwright_executor import ExecutionError, LeaveApprovalExecutor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VerificationOutcome:
    """The result of independently re-reading a record after acting on it."""

    status: VerificationStatus
    observed_status: Optional[str]
    expected_status: Optional[str]
    detail: str

    @property
    def verified(self) -> bool:
        return self.status is VerificationStatus.VERIFIED


def expected_status_after(
    workflow: WorkflowDefinition, decision: DecisionType
) -> Optional[str]:
    """The status label the workflow says should follow this decision, if any."""
    return workflow.verification.expected_status_after.get(decision.value)


def verify_record_status(
    executor: LeaveApprovalExecutor,
    record_id: str,
    workflow: WorkflowDefinition,
    decision: DecisionType,
) -> VerificationOutcome:
    """Re-read `record_id` from the queue screen and judge whether the action took.

    Note the ordering: the expected value is resolved from the workflow definition
    BEFORE the re-read, so there is no way for the observed value to influence what
    counts as correct.
    """
    expected = expected_status_after(workflow, decision)

    if expected is None:
        # Nothing to compare against - say so rather than defaulting to success.
        return VerificationOutcome(
            status=VerificationStatus.NOT_APPLICABLE,
            observed_status=None,
            expected_status=None,
            detail=(
                f"The workflow defines no expected post-action status for "
                f"{decision.value}, so this action cannot be verified by status."
            ),
        )

    try:
        observed = executor.get_current_status(record_id)
    except ExecutionError as exc:
        return VerificationOutcome(
            status=VerificationStatus.FAILED,
            observed_status=None,
            expected_status=expected,
            detail=f"The record's status could not be re-read: {exc}",
        )

    if observed == expected:
        return VerificationOutcome(
            status=VerificationStatus.VERIFIED,
            observed_status=observed,
            expected_status=expected,
            detail=(
                f"Re-read the record from the queue screen: status is {observed}, "
                f"which matches the expected post-action status for {decision.value}."
            ),
        )

    return VerificationOutcome(
        status=VerificationStatus.FAILED,
        observed_status=observed,
        expected_status=expected,
        detail=(
            f"Re-read the record from the queue screen: status is {observed}, but "
            f"{expected} was expected after {decision.value}. The action did not take "
            "effect, so this run is not being reported as successful."
        ),
    )
