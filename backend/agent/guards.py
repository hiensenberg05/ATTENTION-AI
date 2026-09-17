"""Python invariants applied to whatever the LLM returns. NO LLM IN THIS FILE.

The single rule this module exists to enforce:

    THE MODEL MAY ESCALATE. IT MAY NEVER DE-ESCALATE.

`enforce` merges the model's draft with the deterministic policy evaluation by
taking the MORE conservative of the two (see `policy_engine.CONSERVATISM`), then
applies hard constraints that neither party can talk its way past:

  * `allow_auto_rejection: false` means a REJECT draft becomes REVIEW. The reject
    control was never observed being used in Dataset B, so the prototype has no
    evidence of what rejection entails and will not perform one unattended.
  * `allow_auto_approval: false` would likewise force every APPROVE to REVIEW.
  * An APPROVE below `min_confidence_for_auto_execution` becomes REVIEW.
  * A REVIEW always carries `human_review_required=True`.
  * `policy_checks`, `policy_version` and `decided_at` are always the Python
    layer's values. The model does not get to author the audit trail.

Anything the guard changes is recorded in the decision's `reason`, so an operator
reading the UI can see that the override happened rather than only its result.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from models.agent import AgentDecision
from models.common import AmbiguityType, DecisionType

from .policy_engine import CONSERVATISM, PolicyEvaluation
from .schemas import LlmDecisionDraft

#: Marker prefix so overrides are greppable in logs and obvious in the UI.
OVERRIDE_PREFIX = "[guard override]"


def _more_conservative(a: DecisionType, b: DecisionType) -> DecisionType:
    return a if CONSERVATISM[a] >= CONSERVATISM[b] else b


def enforce(
    draft: LlmDecisionDraft,
    evaluation: PolicyEvaluation,
    decided_by: str,
) -> AgentDecision:
    """Turn a model draft plus a deterministic evaluation into the final decision.

    `decided_by` records which path produced the draft - the Groq-backed agent, or
    the deterministic fallback used when the model is unavailable.
    """
    notes: list[str] = []

    confidence = min(1.0, max(0.0, float(draft.confidence)))
    if confidence != draft.confidence:
        notes.append(f"confidence clamped from {draft.confidence} to {confidence}")

    # 1. Merge: escalation propagates, de-escalation does not.
    decision = _more_conservative(draft.decision, evaluation.decision)
    ambiguity: Optional[AmbiguityType] = draft.ambiguity_type
    if decision is not draft.decision:
        notes.append(
            f"model proposed {draft.decision.value}, but the deterministic policy "
            f"evaluation concluded {evaluation.decision.value}; the more conservative "
            "outcome was taken"
        )
        ambiguity = evaluation.ambiguity_type or ambiguity
    elif decision is not evaluation.decision:
        notes.append(
            f"deterministic policy evaluation concluded {evaluation.decision.value}; "
            f"the model escalated to {decision.value}"
        )

    # 2. Hard constraints. Each can only push the outcome towards REVIEW.
    if decision is DecisionType.REJECT and not evaluation.allow_auto_rejection:
        decision = DecisionType.REVIEW
        ambiguity = AmbiguityType.ACTION_NOT_AUTO_EXECUTABLE
        notes.append(
            "auto-rejection is disabled in the policy (the reject control was never "
            "observed being used in Dataset B), so this escalates instead"
        )

    if decision is DecisionType.APPROVE and not evaluation.allow_auto_approval:
        decision = DecisionType.REVIEW
        ambiguity = AmbiguityType.ACTION_NOT_AUTO_EXECUTABLE
        notes.append("auto-approval is disabled in the policy, so this escalates instead")

    if decision is DecisionType.APPROVE and confidence < evaluation.min_confidence:
        decision = DecisionType.REVIEW
        ambiguity = AmbiguityType.LOW_CONFIDENCE
        notes.append(
            f"confidence {confidence:.2f} is below the policy minimum "
            f"{evaluation.min_confidence:.2f} for unattended execution"
        )

    # 3. Consistency. A REVIEW always needs a human and always needs a stated why.
    human_review_required = bool(draft.human_review_required)
    if decision is DecisionType.REVIEW:
        human_review_required = True
        if ambiguity is None:
            ambiguity = evaluation.ambiguity_type or AmbiguityType.CONFLICTING_SIGNALS
    else:
        # An ambiguity type on a non-escalated decision would be misleading in the UI.
        ambiguity = ambiguity if human_review_required else None

    # 4. Assemble the reason. The model's justification is kept, because it is the
    #    readable part; the guard's notes are appended so nothing is silently rewritten.
    reason = draft.reason.strip() or evaluation.reason
    if notes:
        reason = f"{reason} {OVERRIDE_PREFIX} " + "; ".join(notes) + "."

    return AgentDecision(
        decision=decision,
        reason=reason,
        confidence=confidence,
        # Structured, so "how often did Python have to overrule the model?" is a
        # query rather than a regex over prose.
        policy_engine_decision=evaluation.decision,
        model_decision=draft.decision,
        guard_overrides=notes,
        # The audit trail is always the deterministic evaluation's, never the model's.
        policy_checks=evaluation.checks,
        human_review_required=human_review_required,
        ambiguity_type=ambiguity,
        policy_version=evaluation.policy_version,
        decided_at=datetime.now(timezone.utc),
        decided_by=decided_by,
    )
