"""The narrow structured output the LLM is allowed to produce.

Deliberately SMALLER than `models.agent.AgentDecision`. The model is asked for a
judgement and a justification; it is not asked for - and cannot supply - the
policy check results, the policy version, or the decision timestamp. Those are
authored by Python in `guards.enforce`, so the audit trail cannot be hallucinated.

Everything absent from this schema is absent on purpose.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from models.common import AmbiguityType, DecisionType


class LlmDecisionDraft(BaseModel):
    """One model-produced decision draft, before Python invariants are applied."""

    model_config = ConfigDict(extra="forbid")

    decision: DecisionType = Field(
        description=(
            "APPROVE if every policy gate passed and the record is safe to approve "
            "automatically. REVIEW if anything is unclear, missing, or not covered by "
            "the policy. REJECT only if the policy explicitly directs a rejection."
        )
    )
    reason: str = Field(
        description=(
            "Two or three sentences, in English, explaining the decision by referring "
            "to the specific policy gates and record fields. Written for an operations "
            "reviewer, not for a developer."
        )
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How confident you are in this decision. Use a high value only when every "
            "gate was evaluated and passed unambiguously."
        ),
    )
    human_review_required: bool = Field(
        description="True whenever a person must look at this record before anything happens."
    )
    ambiguity_type: Optional[AmbiguityType] = Field(
        default=None,
        description=(
            "Required when human_review_required is true: the category of ambiguity. "
            "MISSING_REQUIRED_DATA when a needed field is absent or unknown; "
            "POLICY_NOT_COVERED when the policy says nothing about this case; "
            "LOW_CONFIDENCE when the rules resolve but you are unsure; "
            "CONFLICTING_SIGNALS when the record contradicts itself; "
            "ACTION_NOT_AUTO_EXECUTABLE when the required action may not be automated."
        ),
    )
