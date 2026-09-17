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

from decimal import Decimal, InvalidOperation

from models.agent import PolicyCheck
from models.common import AmbiguityType, DecisionType
from models.leave import LeaveRequest
from models.payroll import PayrollItem

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
    # Payroll
    "category": "区分 (category)",
    "amount": "金額 (amount)",
    "policy_reference": "参照 (policy_reference)",
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


def _derive(checks: list[PolicyCheck], common: dict[str, Any]) -> PolicyEvaluation:
    """Turn a set of evaluated gates into the decision the rules alone support.

    Deliberately blunt, and identical for every workflow:
      * any gate that FAILED      -> the record is not auto-approvable
      * any gate that is UNKNOWN  -> the record is not auto-approvable
      * all gates passed          -> APPROVE

    Note what is absent: there is no path here that produces REJECT. Both
    workflows disable their negative action (leave 差戻し, payroll
    保留) because neither control was ever observed being used in Dataset B,
    so a violated rule escalates to a human rather than turning into an automatic
    rejection or hold.
    """
    failed = [c for c in checks if c.passed is False]
    unknown = [c for c in checks if c.passed is None]

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
            checks=checks,
            decision=DecisionType.REVIEW,
            ambiguity_type=ambiguity,
            reason=f"Policy gate '{first.check_id}' did not pass. {first.detail}",
            blocking_check_ids=[c.check_id for c in failed],
            **common,
        )

    if unknown:
        first = unknown[0]
        return PolicyEvaluation(
            checks=checks,
            decision=DecisionType.REVIEW,
            ambiguity_type=AmbiguityType.MISSING_REQUIRED_DATA,
            reason=f"Policy gate '{first.check_id}' could not be evaluated. {first.detail}",
            blocking_check_ids=[c.check_id for c in unknown],
            **common,
        )

    return PolicyEvaluation(
        checks=checks,
        decision=DecisionType.APPROVE,
        ambiguity_type=None,
        reason="All policy gates passed; the record is auto-approvable under this policy.",
        blocking_check_ids=[],
        **common,
    )


def _common(policy: dict[str, Any]) -> dict[str, Any]:
    """The guard constraints every evaluation carries, read from the policy.

    `allow_auto_rejection` covers the negative action of whichever workflow this
    is - leave 差戻し or payroll 保留 - so the guard layer needs
    no workflow knowledge at all.
    """
    return dict(
        policy_version=policy.get("policy_version", "unknown"),
        allow_auto_approval=bool(
            policy.get("allow_auto_approval", policy.get("allow_auto_confirmation", False))
        ),
        allow_auto_rejection=bool(
            policy.get("allow_auto_rejection", policy.get("allow_auto_hold", False))
        ),
        min_confidence=float(policy.get("min_confidence_for_auto_execution", 0.8)),
    )


def evaluate_leave_request(
    record: LeaveRequest, policy: dict[str, Any]
) -> PolicyEvaluation:
    """Run every Leave Approval gate and derive the rules-only decision."""
    return _derive(
        [
            _check_status(record, policy),
            _check_required_fields(record, policy),
            _check_request_type(record, policy),
            _check_prior_approval(record, policy),
        ],
        _common(policy),
    )


# ---------------------------------------------------------------------------
# Payroll Confirmation gates
#
# Same three-valued discipline as leave. The one structurally new gate is the
# amount limit, and it carries the heaviest caveat in the whole policy: Dataset
# B's 参照 note showed that approval authority varies by requester type
# (申請者区分 / 承認権限) but NEVER showed the
# thresholds attached to it. The limit is therefore an explicit prototype value,
# and a record above it ESCALATES rather than being refused - the policy has
# nothing to say about it, which is a human's problem, not a rejection.
# ---------------------------------------------------------------------------


def _check_payroll_status(record: PayrollItem, policy: dict[str, Any]) -> PolicyCheck:
    """Gate 1 - is this item still pending?"""
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


def _check_payroll_category(record: PayrollItem, policy: dict[str, Any]) -> PolicyCheck:
    """Gate 3 - is this expense category one the prototype policy recognises?"""
    allowed = list(policy.get("allowed_categories", []))
    description = f"区分 (category) must be one of {', '.join(allowed)}"

    if record.category is None:
        return PolicyCheck(
            check_id="category_allowed",
            description=description,
            passed=None,
            detail="区分 (category) is unknown, so this rule cannot be evaluated.",
        )

    ok = record.category in allowed
    return PolicyCheck(
        check_id="category_allowed",
        description=description,
        passed=ok,
        detail=(
            f"{record.category} is in the policy's auto-confirmable list."
            if ok
            else (
                f"{record.category} is not covered by this policy. It was never observed "
                "being confirmed in Dataset B, so it is not auto-confirmable."
            )
        ),
    )


def _check_policy_reference(record: PayrollItem, policy: dict[str, Any]) -> PolicyCheck:
    """Gate 4 - does the item carry the 参照 note the decision depends on?

    This is payroll's equivalent of leave's prior-approval gate, and it has the
    same shape of evidence gap: the note was visible for the ONE record whose
    detail panel was opened, and is unknown for every record seen only as a list
    row. Unknown escalates; it is never assumed either way.
    """
    description = "参照 (policy_reference) must be present on the record"

    if not policy.get("require_policy_reference", True):
        return PolicyCheck(
            check_id="policy_reference_present",
            description=description,
            passed=True,
            detail="The policy does not require a 参照 note for this workflow.",
        )

    if record.policy_reference:
        return PolicyCheck(
            check_id="policy_reference_present",
            description=description,
            passed=True,
            detail=f"参照: {record.policy_reference}",
        )

    return PolicyCheck(
        check_id="policy_reference_present",
        description=description,
        passed=None,
        detail=(
            "参照 was never read for this item (its detail panel was not opened), "
            "so the applicable approval authority is unknown. Dataset B showed this note "
            "varies by requester type, so it cannot be assumed."
        ),
    )


def _check_amount_within_limit(
    record: PayrollItem, policy: dict[str, Any]
) -> PolicyCheck:
    """Gate 5 - is the amount at or below the explicitly configured prototype limit?"""
    raw_limit = policy.get("auto_approval_amount_limit")
    currency = policy.get("currency", "JPY")
    description = (
        f"金額 (amount) must be at or below the configured prototype limit "
        f"of {raw_limit} {currency}"
    )

    if raw_limit is None:
        return PolicyCheck(
            check_id="amount_within_limit",
            description=description,
            passed=None,
            detail="No auto-approval amount limit is configured, so this cannot be evaluated.",
        )

    if record.amount is None:
        return PolicyCheck(
            check_id="amount_within_limit",
            description=description,
            passed=None,
            detail="金額 (amount) is unknown, so this rule cannot be evaluated.",
        )

    try:
        limit = Decimal(str(raw_limit))
    except (InvalidOperation, ValueError):
        return PolicyCheck(
            check_id="amount_within_limit",
            description=description,
            passed=None,
            detail=f"The configured limit {raw_limit!r} is not a number.",
        )

    ok = record.amount <= limit
    return PolicyCheck(
        check_id="amount_within_limit",
        description=description,
        passed=ok,
        detail=(
            f"{record.amount} {currency} is at or below the prototype limit of {limit}."
            if ok
            else (
                f"{record.amount} {currency} exceeds the prototype limit of {limit}. "
                "Dataset B never revealed the real approval thresholds, so anything above "
                "the configured value escalates rather than being refused."
            )
        ),
    )


def evaluate_payroll_item(
    record: PayrollItem, policy: dict[str, Any]
) -> PolicyEvaluation:
    """Run every Payroll Confirmation gate and derive the rules-only decision."""
    return _derive(
        [
            _check_payroll_status(record, policy),
            _check_required_fields(record, policy),
            _check_payroll_category(record, policy),
            _check_policy_reference(record, policy),
            _check_amount_within_limit(record, policy),
        ],
        _common(policy),
    )
