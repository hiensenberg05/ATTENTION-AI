"""AutomationJob - one complete automation task, start to finish.

This is the object the UI renders, the state machine moves, and the metrics layer
aggregates. It deliberately holds STATE and DECISION as separate fields:

    job.state     -> where we are   (JobState: ... EXECUTING, VERIFYING, COMPLETED)
    job.decision  -> what we decided (AgentDecision.decision: APPROVE/REJECT/REVIEW)

`state_history` exists so the Agent Processing / Execution views can show how the
job got where it is, rather than just its current state - the same auditability
principle applied throughout Phase 1/2.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from state.machine import JobState

from .agent import AgentDecision
from .common import DecisionType, WorkflowType
from .execution import ExecutionResult
from .leave import LeaveRequest
from .payroll import PayrollItem

#: The record under automation. `AutomationJob.workflow` is the practical
#: discriminator: LEAVE_APPROVAL -> LeaveRequest, PAYROLL_CONFIRMATION -> PayrollItem.
BusinessRecord = Union[LeaveRequest, PayrollItem]


class HumanDecision(BaseModel):
    """What a person determined about a record the agent escalated.

    Held SEPARATELY from `AutomationJob.decision` rather than overwriting it, so
    the audit trail keeps both halves of the story: what the agent concluded, and
    what the human then decided. Overwriting would erase the more interesting
    record - the cases where a person disagreed with the policy layer.
    """

    model_config = ConfigDict(extra="forbid")

    decision: DecisionType = Field(description="APPROVE or REJECT; never REVIEW")
    operator: str = Field(description="Who authorised it")
    note: str = Field(min_length=1, description="Mandatory audit note - why")
    at: datetime

    @field_validator("decision")
    @classmethod
    def _must_be_actionable(cls, value: DecisionType) -> DecisionType:
        if value is DecisionType.REVIEW:
            raise ValueError("A human determination must resolve the record, not re-escalate it.")
        return value


class StateTransition(BaseModel):
    """One move through the state machine, for the audit trail."""

    model_config = ConfigDict(extra="forbid")

    from_state: JobState
    to_state: JobState
    at: datetime
    note: Optional[str] = None


class AutomationJob(BaseModel):
    """One record being taken through one workflow."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    workflow: WorkflowType
    state: JobState = JobState.START

    record: BusinessRecord

    decision: Optional[AgentDecision] = Field(
        default=None, description="Set once POLICY_CHECK has run. Independent of `state`."
    )
    human_decision: Optional[HumanDecision] = Field(
        default=None,
        description=(
            "Set when an operator resolved a record the agent escalated. Coexists "
            "with `decision`; it does not replace it."
        ),
    )
    execution: Optional[ExecutionResult] = Field(
        default=None, description="Set once EXECUTING/VERIFYING has run."
    )

    state_history: list[StateTransition] = Field(default_factory=list)
    error: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    @property
    def record_id(self) -> str:
        """Convenience accessor - both record types expose `record_id`."""
        return self.record.record_id
