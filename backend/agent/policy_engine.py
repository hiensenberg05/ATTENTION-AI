"""Deterministic evaluation of the explicit prototype policy. NO LLM IN THIS FILE.

This module is the reason the prototype can claim its decisions are explainable:
every gate below is a plain Python comparison against a value in
`data/policies.json`, and each one produces a `PolicyCheck` that the UI renders
verbatim. If this module says a record is approvable, that conclusion is
reproducible without a model, without a network call, and without a temperature.

The three-valued `PolicyCheck.passed` is load-bearing:

    True  - the rule was evaluated and satisfied
    False - the rule was evaluated and violated
    None  - the rule COULD NOT be evaluated, because the field it needs is unknown

`None` is not a soft `False`. Phase 2's visual audit established that Dataset B's
UI showed whether prior approval was REQUIRED but never whether it was OBTAINED,
so "unknown" is the honest state of a real field, and it must escalate to a human
rather than be resolved in either direction by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from models.agent import PolicyCheck
from models.common import AmbiguityType, DecisionType
from models.leave import LeaveRequest

#: Ordering used whenever two opinions about a record must be merged.
#: Higher = more conservative. Merging always takes the maximum, so the pipeline
#: can only ever escalate - see `guards.enforce`.
CONSERVATISM: dict[DecisionType, int] = {
    DecisionType.APPROVE: 0,
    DecisionType.REJECT: 1,
    DecisionType.REVIEW: 2,
}

#: Human-readable labels for the record fields the policy can require, so a
#: missing-field message reads like the HR screen rather than like a schema.
FIELD_LABELS: dict[str, str] = {
    "employee_id": "社員ID (employee_id)",
    "employee_name": "氏名 (employee_name)",
    "request_type": "申請種別 (request_type)",
    "request_date": "期間 (request_date)",
    "department": "所属部署 (department)",
}


@dataclass(frozen=True)
class PolicyEvaluation:
    """What the rules alone conclude about one record, before any LLM is asked."""

    policy_version: str
    checks: list[PolicyCheck]
    decision: DecisionType
    ambiguity_type: Optional[AmbiguityType]
    reason: str

    #: Constraints the guard layer enforces regardless of what the model returns.
    allow_auto_approval: bool = True
    allow_auto_rejection: bool = False
    min_confidence: float = 0.8

    blocking_check_ids: list[str] = field(default_factory=list)

    @property
    def has_unevaluable_check(self) -> bool:
        return any(c.passed is None for c in self.checks)

    @property
    def has_failed_check(self) -> bool:
        return any(c.passed is False for c in self.checks)


def _check_status(record: LeaveRequest, policy: dict[str, Any]) -> PolicyCheck:
    """Gate 1 - is this record in a status the workflow is allowed to act on?"""
    actionable = list(policy.get("actionable_statuses", []))
    current = record.status.value
    ok = current in actionable
    return PolicyCheck(
        check_id="status_actionable",
        description=f"Status must be one of {', '.join(actionable)}",
        passed=ok,
        detail=(
            f"Status is {current}, which is actionable."
            if ok
            else f"Status is {current}; the workflow only acts on {', '.join(actionable)}."
        ),
    )


def _check_required_fields(record: LeaveRequest, policy: dict[str, Any]) -> PolicyCheck:
    """Gate 2 - does the record carry every field the policy needs to decide?"""
    required = list(policy.get("required_fields", []))
    missing = [f for f in required if getattr(record, f, None) in (None, "")]
    ok = not missing
    return PolicyCheck(
        check_id="required_fields_present",
        description=f"All required fields present: {', '.join(required)}",
        passed=ok,
        detail=(
            "Every required field is populated."
            if ok
            else "Missing: " + ", ".join(FIELD_LABELS.get(f, f) for f in missing)
        ),
    )


def _check_request_type(record: LeaveRequest, policy: dict[str, Any]) -> PolicyCheck:
    """Gate 3 - is this request type one the policy covers?

    Not-covered is deliberately distinct from not-allowed: an unseen request type
    means the policy has nothing to say, which is a human's problem, not a
    rejection.
    """
    allowed = list(policy.get("allowed_request_types", []))
    description = f"Request type must be one of {', '.join(allowed)}"

    if record.request_type is None:
        return PolicyCheck(
            check_id="request_type_allowed",
            description=description,
            passed=None,
            detail=(
                "申請種別 (request_type) is unknown, so this rule "
                "cannot be evaluated."
            ),
        )

    ok = record.request_type in allowed
    return PolicyCheck(
        check_id="request_type_allowed",
        description=description,
        passed=ok,
        detail=(
            f"{record.request_type} is in the policy's auto-approvable list."
            if ok
            else (
                f"{record.request_type} is not covered by this policy. It was never "
                "observed being approved in Dataset B, so it is not auto-approvable."
            )
        ),
    )


def _check_prior_approval(record: LeaveRequest, policy: dict[str, Any]) -> PolicyCheck:
    """Gate 4 - the prior-approval rule, read straight out of the policy rule table.

    The branch outcomes are NOT hardcoded here; they come from
    `leave_approval.prior_approval_rule` so the policy stays the single place the
    business behaviour is written down.
    """
    rule = policy.get("prior_approval_rule", {})
    required = record.prior_approval_required
    obtained = record.prior_approval_obtained
    flag = "事前承認要否"  # 事前承認要否
    description = (
        f"{flag} (prior approval) must be resolved: not required, or required and obtained"
    )

    if required is None:
        branch, passed = "when_requirement_unknown", None
        detail = (
            f"{flag} was never read for this record (its detail panel was not opened), "
            "so whether prior approval applies is unknown."
        )
    elif required is False:
        branch, passed = "when_not_required", True
        detail = f"{flag}: 不要 - no prior approval is needed."
    elif obtained is True:
        branch, passed = "when_required_and_obtained", True
        detail = f"{flag}: 要, and prior approval is recorded as obtained."
    elif obtained is False:
        branch, passed = "when_required_and_not_obtained", False
        detail = f"{flag}: 要, but prior approval was not obtained."
    else:
        branch, passed = "when_required_and_unknown", None
        detail = (
            f"{flag}: 要, but whether approval was actually obtained is unknown. "
            "Dataset B's UI never exposed this, so it cannot be assumed either way."
        )

    outcome = rule.get(branch, "REVIEW")
    return PolicyCheck(
        check_id="prior_approval_resolved",
        description=description,
        passed=passed,
        detail=f"{detail} Policy rule '{branch}' -> {outcome}.",
    )


def evaluate_leave_request(
    record: LeaveRequest, policy: dict[str, Any]
) -> PolicyEvaluation:
    """Run every gate and derive the decision the rules alone support.

    The derivation is intentionally blunt:
      * any gate that FAILED      -> the record is not auto-approvable
      * any gate that is UNKNOWN  -> the record is not auto-approvable
      * all gates passed          -> APPROVE

    Note what is absent: there is no path here that produces REJECT. The policy
    sets `allow_auto_rejection: false` because the reject control was never once
    observed being used in Dataset B, so a violated rule escalates to a human
    rather than turning into an automatic rejection.
    """
    checks = [
        _check_status(record, policy),
        _check_required_fields(record, policy),
        _check_request_type(record, policy),
        _check_prior_approval(record, policy),
    ]

    failed = [c for c in checks if c.passed is False]
    unknown = [c for c in checks if c.passed is None]

    common = dict(
        policy_version=policy.get("policy_version", "unknown"),
        checks=checks,
        allow_auto_approval=bool(policy.get("allow_auto_approval", False)),
        allow_auto_rejection=bool(policy.get("allow_auto_rejection", False)),
        min_confidence=float(policy.get("min_confidence_for_auto_execution", 0.8)),
    )

    if failed:
        first = failed[0]
        # A missing-field failure is a data problem; anything else is the policy
        # declining to cover the case. The distinction drives different copy and
        # different operator actions in the review queue.
        ambiguity = (
            AmbiguityType.MISSING_REQUIRED_DATA
            if first.check_id == "required_fields_present"
            else AmbiguityType.POLICY_NOT_COVERED
        )
        return PolicyEvaluation(
            decision=DecisionType.REVIEW,
            ambiguity_type=ambiguity,
            reason=f"Policy gate '{first.check_id}' did not pass. {first.detail}",
            blocking_check_ids=[c.check_id for c in failed],
            **common,
        )

    if unknown:
        first = unknown[0]
        return PolicyEvaluation(
            decision=DecisionType.REVIEW,
            ambiguity_type=AmbiguityType.MISSING_REQUIRED_DATA,
            reason=f"Policy gate '{first.check_id}' could not be evaluated. {first.detail}",
            blocking_check_ids=[c.check_id for c in unknown],
            **common,
        )

    return PolicyEvaluation(
        decision=DecisionType.APPROVE,
        ambiguity_type=None,
        reason="All policy gates passed; the record is auto-approvable under this policy.",
        blocking_check_ids=[],
        **common,
    )
