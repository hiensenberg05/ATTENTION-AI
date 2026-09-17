"""Tests for the deterministic half of the decision layer.

Nothing here calls Groq. These tests exist to prove that the parts of the system
which must be reproducible ARE reproducible: the policy gates, and the invariants
that constrain whatever the model returns.
"""

from __future__ import annotations

import pytest

import repository
from agent.guards import enforce
from agent.policy_engine import evaluate_leave_request
from agent.schemas import LlmDecisionDraft
from models.common import AmbiguityType, DecisionType, LeaveStatus


@pytest.fixture(scope="module")
def policy() -> dict:
    return repository.get_policy("leave_approval")


def record(record_id: str):
    return repository.get_leave_request(record_id)


def gate(evaluation, check_id):
    return next(c for c in evaluation.checks if c.check_id == check_id)


# -- the three-valued gate logic ---------------------------------------------


def test_clean_record_passes_every_gate(policy):
    ev = evaluate_leave_request(record("DEMO-LV-001"), policy)
    assert [c.passed for c in ev.checks] == [True, True, True, True]
    assert ev.decision is DecisionType.APPROVE
    assert ev.ambiguity_type is None


def test_unknown_prior_approval_is_not_evaluable_rather_than_failed(policy):
    """The Dataset B record: approval is REQUIRED, but obtained is genuinely unknown."""
    ev = evaluate_leave_request(record("P2-07048822-006"), policy)
    check = gate(ev, "prior_approval_resolved")
    assert check.passed is None, "unknown must not collapse to False"
    assert ev.decision is DecisionType.REVIEW
    assert ev.ambiguity_type is AmbiguityType.MISSING_REQUIRED_DATA


def test_prior_approval_required_but_not_obtained_is_a_failure(policy):
    ev = evaluate_leave_request(record("DEMO-LV-005"), policy)
    assert gate(ev, "prior_approval_resolved").passed is False
    assert ev.decision is DecisionType.REVIEW


def test_request_type_outside_the_policy_escalates_rather_than_rejecting(policy):
    """年次有給休暇 was never observed being approved, so the policy excludes it."""
    ev = evaluate_leave_request(record("DEMO-LV-006"), policy)
    assert gate(ev, "request_type_allowed").passed is False
    assert ev.decision is DecisionType.REVIEW
    assert ev.ambiguity_type is AmbiguityType.POLICY_NOT_COVERED


def test_missing_required_fields_are_named(policy):
    ev = evaluate_leave_request(record("DEMO-LV-008"), policy)
    check = gate(ev, "required_fields_present")
    assert check.passed is False
    assert "employee_id" in check.detail and "department" in check.detail


def test_already_processed_record_is_not_actionable(policy):
    ev = evaluate_leave_request(record("DEMO-LV-010"), policy)
    assert gate(ev, "status_actionable").passed is False
    assert ev.decision is DecisionType.REVIEW


def test_the_policy_engine_can_never_produce_a_rejection(policy):
    """No input in the demo set should yield REJECT - auto-rejection is disabled."""
    for rec in repository.get_leave_requests():
        assert evaluate_leave_request(rec, policy).decision is not DecisionType.REJECT


# -- the guard invariants ----------------------------------------------------


def draft(decision: DecisionType, confidence: float = 0.95, **kw) -> LlmDecisionDraft:
    return LlmDecisionDraft(
        decision=decision,
        reason=kw.pop("reason", "model reasoning"),
        confidence=confidence,
        human_review_required=kw.pop(
            "human_review_required", decision is DecisionType.REVIEW
        ),
        ambiguity_type=kw.pop("ambiguity_type", None),
    )


def test_the_model_cannot_approve_a_record_the_policy_escalated(policy):
    ev = evaluate_leave_request(record("P2-07048822-006"), policy)
    out = enforce(draft(DecisionType.APPROVE, 0.99), ev, "test")
    assert out.decision is DecisionType.REVIEW
    assert out.human_review_required is True
    assert "[guard override]" in out.reason


def test_the_model_can_escalate_a_record_the_policy_approved(policy):
    """Escalation propagates in the other direction; only de-escalation is blocked."""
    ev = evaluate_leave_request(record("DEMO-LV-001"), policy)
    out = enforce(
        draft(DecisionType.REVIEW, 0.4, ambiguity_type=AmbiguityType.CONFLICTING_SIGNALS),
        ev,
        "test",
    )
    assert out.decision is DecisionType.REVIEW
    assert out.human_review_required is True


def test_a_rejection_is_always_converted_to_review(policy):
    """allow_auto_rejection is false, so REJECT must never survive the guard."""
    ev = evaluate_leave_request(record("DEMO-LV-001"), policy)
    out = enforce(draft(DecisionType.REJECT, 0.99), ev, "test")
    assert out.decision is DecisionType.REVIEW
    assert out.ambiguity_type is AmbiguityType.ACTION_NOT_AUTO_EXECUTABLE


def test_low_confidence_approval_is_escalated(policy):
    ev = evaluate_leave_request(record("DEMO-LV-001"), policy)
    out = enforce(draft(DecisionType.APPROVE, 0.4), ev, "test")
    assert out.decision is DecisionType.REVIEW
    assert out.ambiguity_type is AmbiguityType.LOW_CONFIDENCE


def test_confidence_at_the_threshold_is_allowed(policy):
    ev = evaluate_leave_request(record("DEMO-LV-001"), policy)
    out = enforce(draft(DecisionType.APPROVE, ev.min_confidence), ev, "test")
    assert out.decision is DecisionType.APPROVE


def test_the_audit_trail_is_always_the_deterministic_one(policy):
    """The model supplies no policy checks, and cannot overwrite them."""
    ev = evaluate_leave_request(record("DEMO-LV-005"), policy)
    out = enforce(draft(DecisionType.APPROVE, 0.99), ev, "test")
    assert [c.model_dump() for c in out.policy_checks] == [
        c.model_dump() for c in ev.checks
    ]
    assert out.policy_version == ev.policy_version
    assert out.decided_at is not None
    assert out.decided_by == "test"


def test_review_always_carries_a_stated_ambiguity(policy):
    ev = evaluate_leave_request(record("P2-07048822-006"), policy)
    out = enforce(draft(DecisionType.REVIEW, 0.3), ev, "test")
    assert out.ambiguity_type is not None


def test_every_demo_record_survives_a_hostile_model(policy):
    """Whatever the model says, no record the policy escalated may be auto-approved."""
    for rec in repository.get_leave_requests():
        ev = evaluate_leave_request(rec, policy)
        out = enforce(draft(DecisionType.APPROVE, 1.0), ev, "test")
        if ev.decision is not DecisionType.APPROVE:
            assert out.decision is DecisionType.REVIEW, rec.record_id
        assert out.decision is not DecisionType.REJECT


def test_pending_status_is_the_only_actionable_one(policy):
    assert policy["actionable_statuses"] == [LeaveStatus.PENDING.value]
