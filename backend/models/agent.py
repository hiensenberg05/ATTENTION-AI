"""AgentDecision - the structured output the future agent layer will produce.

SCHEMA ONLY. No LLM is called anywhere in this module and none is imported. This
is the contract the later PydanticAI-backed agent must satisfy, defined now so the
state machine, FastAPI layer and UI can be built against a stable shape.

Design rule carried from the architecture discussion: the agent applies an
EXPLICIT, human-authored policy (see `data/policies.json`) to an already-structured
record. It does not invent business rules, and it does not control the browser.
Dataset B's logs never revealed the company's real approval policy - only that
some action was taken - so `policy_version` records which prototype policy was
applied, and nothing here should be read as "the real policy was learned".
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import AmbiguityType, DecisionType


class PolicyCheck(BaseModel):
    """One named rule evaluated against one record.

    `passed=None` means the check COULD NOT BE EVALUATED (e.g. the field it needs
    is unknown), which is different from the check failing. That distinction is
    what routes a record to human review instead of to a rejection.
    """

    model_config = ConfigDict(extra="forbid")

    check_id: str = Field(description="Stable id, e.g. 'request_type_allowed'")
    description: str = Field(description="Human-readable statement of the rule")
    passed: Optional[bool] = Field(
        default=None, description="True=passed, False=failed, None=not evaluable"
    )
    detail: Optional[str] = Field(
        default=None, description="Why it passed/failed/could not be evaluated"
    )


class AgentDecision(BaseModel):
    """The structured decision for one record. A decision is not a state."""

    model_config = ConfigDict(extra="forbid")

    decision: DecisionType
    reason: str = Field(description="Short human-readable justification, shown in the UI")
    confidence: float = Field(ge=0.0, le=1.0)
    policy_checks: list[PolicyCheck] = Field(default_factory=list)
    human_review_required: bool

    ambiguity_type: Optional[AmbiguityType] = Field(
        default=None,
        description="Set when human_review_required is True; says WHY it escalated.",
    )
    policy_version: Optional[str] = Field(
        default=None, description="Which prototype policy version was applied"
    )
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = Field(
        default=None,
        description=(
            "Which path produced this decision: 'llm+policy_guard' when the Groq-backed "
            "agent drafted it, or 'policy_engine_fallback' when the model was "
            "unavailable and the deterministic rules decided alone. Recorded because a "
            "reviewer should know whether a model was involved at all."
        ),
    )

    @model_validator(mode="after")
    def _review_implies_human_review(self) -> "AgentDecision":
        """A REVIEW decision must always flag human review; the reverse is allowed.

        (A low-confidence APPROVE may also require human review without the
        decision itself being REVIEW.)
        """
        if self.decision is DecisionType.REVIEW and not self.human_review_required:
            raise ValueError("decision=REVIEW requires human_review_required=True")
        return self
