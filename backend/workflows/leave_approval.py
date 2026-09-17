"""The Leave Approval workflow definition - workflow #1, the first MVP target.

Specification only: no agent, no browser, no state transitions are executed here.

The step sequence mirrors the human action sequence directly confirmed by
screenshot in `phase2/results/visual_audit.md` for segment
`ses_20260701-180923-NEELA9BAF::seg013` (4.4s, 17 events):

    click into a row -> scroll to the detail panel -> read the fields and the
    reference note -> click 承認 -> (optional comment) -> submit -> next record

Why this workflow is first: of the two visually-confirmed clean workflows it has
the smaller surface - single system, no cross-port navigation, and a decision
point with an EXPLICIT on-screen flag (事前承認要否) rather than an implicit
policy note. It is the lowest-risk case on which to prove the platform pattern.
"""

from __future__ import annotations

from models.common import DecisionType, WorkflowType
from models.execution import ExecutionAction
from state.machine import JobState

from .base import (
    ExecutionActionSpec,
    VerificationSpec,
    WorkflowDefinition,
    WorkflowEvidence,
    WorkflowStepSpec,
)

LEAVE_APPROVAL_WORKFLOW = WorkflowDefinition(
    workflow=WorkflowType.LEAVE_APPROVAL,
    name="Leave Approval",
    description=(
        "Review one pending leave/attendance request against an explicit prototype "
        "policy and either approve it, return it, or escalate it to a human."
    ),
    implemented=True,  # agent + Playwright executor + verification are live
    record_model="LeaveRequest",
    policy_key="leave_approval",
    steps=[
        WorkflowStepSpec(
            step_id="load_request",
            name="Load pending request",
            description="Fetch one pending leave request from the queue.",
            state=JobState.LOADING,
            automated=True,
        ),
        WorkflowStepSpec(
            step_id="validate_request",
            name="Validate required information",
            description=(
                "Check the record carries every field the policy needs. Incomplete "
                "records escalate to human review rather than failing."
            ),
            state=JobState.VALIDATING,
            automated=True,
        ),
        WorkflowStepSpec(
            step_id="analyze",
            name="Analyze relevant fields",
            description=(
                "Extract the decision-relevant fields: request type, date, department, "
                "and the 事前承認要否 prior-approval flag."
            ),
            state=JobState.ANALYZING,
            automated=True,
        ),
        WorkflowStepSpec(
            step_id="policy_check",
            name="Evaluate configured policy",
            description=(
                "Apply the explicit prototype policy in data/policies.json and produce "
                "a structured decision with per-rule check results."
            ),
            state=JobState.POLICY_CHECK,
            automated=True,
        ),
        WorkflowStepSpec(
            step_id="human_review",
            name="Human review",
            description=(
                "A person resolves records the policy could not decide. The platform "
                "must not act automatically on these."
            ),
            state=JobState.HUMAN_REVIEW,
            automated=False,
        ),
        WorkflowStepSpec(
            step_id="execute",
            name="Execute decision in the HR system",
            description=(
                "Deterministically open the record and click the decided control. "
                "No judgement is made at this step."
            ),
            state=JobState.EXECUTING,
            automated=True,
        ),
        WorkflowStepSpec(
            step_id="verify",
            name="Verify resulting status",
            description=(
                "Re-read the record's status and confirm it actually changed. Clicking "
                "successfully is not the same as the record being approved."
            ),
            state=JobState.VERIFYING,
            automated=True,
        ),
    ],
    supported_decisions=[DecisionType.APPROVE, DecisionType.REJECT, DecisionType.REVIEW],
    execution_actions=[
        ExecutionActionSpec(
            decision=DecisionType.APPROVE,
            action=ExecutionAction.APPROVE_LEAVE,
            ui_target_label="承認",
            auto_executable=True,
            rationale=(
                "The approve path was directly observed end to end in Dataset B "
                "(segment ses_20260701-180923-NEELA9BAF::seg013)."
            ),
        ),
        ExecutionActionSpec(
            decision=DecisionType.REJECT,
            action=ExecutionAction.REJECT_LEAVE,
            ui_target_label="差戻し",
            auto_executable=False,
            rationale=(
                "The 差戻し button exists in the UI but was NEVER observed being used "
                "in any inspected Dataset B segment. With no evidence of what rejection "
                "requires (mandatory reason? downstream notification?), the prototype "
                "does not auto-execute it; such records go to human review."
            ),
        ),
    ],
    verification=VerificationSpec(
        method="Re-read the record's status field after submitting and compare it "
        "against the expected post-action label.",
        status_before="申請中",
        expected_status_after={
            DecisionType.APPROVE.value: "承認済み",
            DecisionType.REJECT.value: "差戻し",
        },
        expected_status_observed_in_dataset_b=False,
        note=(
            "PROTOTYPE ASSUMPTION. No approved or returned leave record was captured "
            "in any inspected Dataset B segment, so the post-action status labels are "
            "assumed, not observed. They are configurable and must be confirmed against "
            "whatever system the executor is eventually pointed at."
        ),
    ),
    evidence=WorkflowEvidence(
        process_type_id="B-127.0.0.1_5132_leave-applications",
        observed_executions=23,
        observed_minutes=18.63,
        observed_workers=3,
        observed_sessions=6,
        family_median_duration_seconds=40.83,
        clean_instance_segment_id="ses_20260701-180923-NEELA9BAF::seg013",
        clean_instance_duration_seconds=4.365,
        clean_instance_event_count=17,
        phase2_confidence_level="High",
        visually_confirmed=True,
        source_documents=[
            "phase2/results/phase2_summary.md",
            "phase2/results/visual_audit.md",
            "phase2/results/step3_prototype_spec.md",
            "phase2/results/automation_candidates.csv",
        ],
        caveats=[
            "Only 30.5% of Phase 2 segments were single-app/single-route; family-level "
            "counts likely undercount true executions and overcount per-execution time.",
            "The reject (差戻し) path was never observed in any inspected segment.",
            "Dataset B never revealed the company's real approval policy, only that an "
            "action was taken. The policy used here is an explicit prototype stand-in.",
        ],
    ),
)
