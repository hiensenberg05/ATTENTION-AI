"""ExecutionResult - the structured record of deterministic browser execution.

SCHEMA ONLY. Playwright is not imported, installed or invoked anywhere here. This
is the shape the later executor must produce, defined now so the Execution View in
the UI and the metrics layer can be built against it.

Design rule: execution is mechanical. By the time anything in this module is
produced, the decision has already been made (by policy evaluation, or by a human
in the review path). The executor's only jobs are: perform the action that was
decided, and then independently VERIFY that the record's status actually changed.
Clicking successfully is not the same as the record being approved, which is why
`success` (did the actions run) and `verification_status` (did reality change) are
separate fields rather than one boolean.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import WorkflowType


class ExecutionAction(str, Enum):
    """The concrete UI action to perform, derived from a decision + workflow.

    The Japanese labels in the comments are the actual button labels observed in
    the Dataset B screenshots.
    """

    APPROVE_LEAVE = "APPROVE_LEAVE"  # 承認 button
    REJECT_LEAVE = "REJECT_LEAVE"  # 差戻し button - NEVER OBSERVED being used
    CONFIRM_PAYROLL = "CONFIRM_PAYROLL"  # 登録確定 button (workflow 2, not implemented)
    HOLD_PAYROLL = "HOLD_PAYROLL"  # 保留 button - NEVER OBSERVED being used


class VerificationStatus(str, Enum):
    """Did the record's real status actually change as expected?"""

    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ExecutionStep(BaseModel):
    """One deterministic step of the execution, for the step-by-step UI view.

    Step names mirror the human action sequence confirmed in `visual_audit.md`:
    open the queue, locate the record, open its detail panel, click the decision
    button, submit, then re-read the status.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    completed: bool = False
    detail: Optional[str] = None
    error: Optional[str] = None
    at: Optional[datetime] = None


class ExecutionResult(BaseModel):
    """Outcome of executing one decided action against one record."""

    model_config = ConfigDict(extra="forbid")

    action: ExecutionAction
    workflow: WorkflowType
    record_id: str

    success: bool = Field(description="Did every execution step complete without error?")
    steps_completed: list[ExecutionStep] = Field(default_factory=list)

    verification_status: VerificationStatus = VerificationStatus.NOT_ATTEMPTED
    status_before: Optional[str] = Field(
        default=None, description="Record status read before acting, e.g. 申請中"
    )
    status_after: Optional[str] = Field(
        default=None, description="Record status read after acting"
    )

    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Real measured execution time. Populated by the executor only - "
        "never estimated, since run metrics must come from actual runs.",
    )

    executed_by: Optional[str] = Field(
        default=None,
        description="'agent' for policy-driven execution, or a human identifier when "
        "the action was authorised in the human-review path.",
    )
