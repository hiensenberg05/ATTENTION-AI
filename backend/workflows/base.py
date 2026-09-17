"""Declarative workflow specification types.

A WorkflowDefinition describes a workflow as DATA rather than as code, so that:
  - the later agent layer reads its steps/policy key instead of hard-coding them,
  - the later executor reads its action specs instead of hard-coding selectors,
  - the UI can render workflow cards (including the Phase 2 evidence numbers)
    without the frontend re-deriving anything,
  - adding Payroll Confirmation later means adding one definition, not editing
    the engine.

Nothing here executes anything. These are specifications only.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from models.common import DecisionType, WorkflowType
from models.execution import ExecutionAction
from state.machine import JobState


class WorkflowStepSpec(BaseModel):
    """One step of the workflow, bound to the state it runs in."""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    name: str
    description: str
    state: JobState = Field(description="The JobState this step executes in")
    automated: bool = Field(description="False = requires a human")


class ExecutionActionSpec(BaseModel):
    """How a decision becomes a concrete UI action.

    `ui_target_label` records the literal on-screen control observed in Dataset B.
    Actual selectors belong to the later Playwright layer, not here.
    """

    model_config = ConfigDict(extra="forbid")

    decision: DecisionType
    action: ExecutionAction
    ui_target_label: str = Field(description="Observed button label, e.g. 承認")
    auto_executable: bool = Field(
        description=(
            "May the platform perform this action without a human? False where "
            "Dataset B provides no evidence of the action ever being taken."
        )
    )
    rationale: str


class VerificationSpec(BaseModel):
    """How to confirm the action actually changed the record."""

    model_config = ConfigDict(extra="forbid")

    method: str = Field(description="How verification is performed")
    status_before: str = Field(description="Expected status prior to acting")
    expected_status_after: dict[str, str] = Field(
        description="decision value -> expected status label afterwards"
    )
    expected_status_observed_in_dataset_b: bool = Field(
        description="Whether the post-action label was actually seen in Dataset B"
    )
    note: Optional[str] = None


class WorkflowEvidence(BaseModel):
    """Provenance tying this workflow back to the Phase 1/2 analysis.

    These are HISTORICAL numbers measured in Phase 2 from Dataset B. They are not
    prototype run metrics - live automation rate / error rate / execution time must
    come from actual prototype runs and are tracked separately.
    """

    model_config = ConfigDict(extra="forbid")

    dataset: str = "dataset_b"
    process_type_id: str
    observed_executions: int
    observed_minutes: float
    observed_workers: int
    observed_sessions: int
    family_median_duration_seconds: float
    clean_instance_segment_id: str
    clean_instance_duration_seconds: float
    clean_instance_event_count: int
    phase2_confidence_level: str
    visually_confirmed: bool
    source_documents: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class WorkflowDefinition(BaseModel):
    """A complete, declarative description of one automatable workflow."""

    model_config = ConfigDict(extra="forbid")

    workflow: WorkflowType
    name: str
    description: str
    implemented: bool = Field(description="False = declared but not built yet")

    record_model: str = Field(description="Name of the Pydantic record model used")
    policy_key: str = Field(description="Key into data/policies.json")

    steps: list[WorkflowStepSpec]
    supported_decisions: list[DecisionType]
    execution_actions: list[ExecutionActionSpec]
    verification: VerificationSpec
    evidence: WorkflowEvidence
