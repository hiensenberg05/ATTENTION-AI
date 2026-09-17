"""The Payroll Confirmation workflow definition - workflow #2.

Specification only: no agent, no browser, no state transitions are executed here.

The step sequence mirrors the human action sequence directly confirmed by
screenshot in `phase2/results/visual_audit.md` for segment
`ses_20260701-190250-NEELA9BAF::seg002` (11.7s, 24 events), reconstructed
event-by-event in `step3_prototype_spec.md`:

    navigate to the 5132 payroll-items list -> click into a row -> scroll to the
    detail panel -> read 管理ID / 社員ID / 区分 / 金額 / ステータス and the 参照
    note -> click 登録確定 -> short comment -> form commits -> next record

WHY THIS IS THE SECOND WORKFLOW, NOT THE FIRST. Its process family is larger than
leave by both execution count and total observed time, but its decision logic is
LESS explicit on screen: the 参照 note shows that approval authority varies by
requester type (`申請者区分：regular　承認権限：部門長`) without ever revealing the
thresholds that go with it. Leave's 事前承認要否 flag is a single explicit yes/no.
So leave was the lower-risk case on which to prove the pattern, and payroll is the
proof that the pattern generalises - which is the actual product claim.

Reused wholesale from workflow #1: the state machine, the orchestrator, the guard
layer, the decision agent, the executor, verification, the audit trail and the UI.
What is workflow-specific is this file, a policy section, a screen spec and a set
of policy gates.
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

PAYROLL_CONFIRMATION_WORKFLOW = WorkflowDefinition(
    workflow=WorkflowType.PAYROLL_CONFIRMATION,
    name="Payroll Confirmation",
    description=(
        "Review one pending payroll/expense line item against an explicit prototype "
        "policy and either confirm it, hold it, or escalate it to a human."
    ),
    implemented=True,
    record_model="PayrollItem",
    policy_key="payroll_confirmation",
    steps=[
        WorkflowStepSpec(
            step_id="load_item",
            name="Load pending payroll item",
            description="Fetch one pending line item from the expense/salary queue.",
            state=JobState.LOADING,
            automated=True,
        ),
        WorkflowStepSpec(
            step_id="validate_item",
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
                "Extract the decision-relevant fields: category, amount, and the 参照 "
                "policy-reference note."
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
            name="Execute decision in the payroll system",
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
                "Re-read the record's status from the queue screen and confirm it "
                "actually changed. Clicking successfully is not the same as the item "
                "being confirmed."
            ),
            state=JobState.VERIFYING,
            automated=True,
        ),
    ],
    supported_decisions=[DecisionType.APPROVE, DecisionType.REJECT, DecisionType.REVIEW],
    execution_actions=[
        ExecutionActionSpec(
            decision=DecisionType.APPROVE,
            action=ExecutionAction.CONFIRM_PAYROLL,
            ui_target_label="登録確定",
            auto_executable=True,
            rationale=(
                "The confirm path was directly observed end to end in Dataset B "
                "(segment ses_20260701-190250-NEELA9BAF::seg002, record "
                "P1-07046967-001)."
            ),
        ),
        ExecutionActionSpec(
            decision=DecisionType.REJECT,
            action=ExecutionAction.HOLD_PAYROLL,
            ui_target_label="保留",
            auto_executable=False,
            rationale=(
                "The 保留 (hold) button exists in the UI but was NEVER observed "
                "being used in any inspected Dataset B segment. With no evidence of what "
                "triggers a hold or what it obliges downstream, the prototype does not "
                "auto-execute it; such records go to human review. This is the same rule, "
                "for the same reason, as leave rejection."
            ),
        ),
    ],
    verification=VerificationSpec(
        method="Re-read the item's status from the queue screen after submitting and "
        "compare it against the expected post-action label.",
        status_before="未処理",
        expected_status_after={
            DecisionType.APPROVE.value: "登録確定済み",
            DecisionType.REJECT.value: "保留",
        },
        expected_status_observed_in_dataset_b=False,
        note=(
            "PROTOTYPE ASSUMPTION. No confirmed or held payroll item was captured in any "
            "inspected Dataset B segment - only the 登録確定 / 保留 button labels were. "
            "The post-action status labels are therefore derived from those labels rather "
            "than observed, are configurable, and must be confirmed against whatever "
            "system the executor is eventually pointed at."
        ),
    ),
    evidence=WorkflowEvidence(
        process_type_id="B-127.0.0.1_5132_payroll-items",
        observed_executions=39,
        observed_minutes=30.16,
        observed_workers=4,
        observed_sessions=10,
        family_median_duration_seconds=28.82,
        clean_instance_segment_id="ses_20260701-190250-NEELA9BAF::seg002",
        clean_instance_duration_seconds=11.7,
        clean_instance_event_count=24,
        phase2_confidence_level="High",
        visually_confirmed=True,
        source_documents=[
            "phase2/results/phase2_summary.md",
            "phase2/results/visual_audit.md",
            "phase2/results/step3_prototype_spec.md",
            "phase2/results/automation_candidates.csv",
        ],
        caveats=[
            "These figures are for the port-5132 payroll family alone. Dataset B also "
            "shows payroll-items activity on ports 5133 (7 executions) and 5134 (15), "
            "which this prototype does not cover - 61 observed payroll executions in "
            "total across the three.",
            "Only 30.5% of Phase 2 segments were single-app/single-route; family-level "
            "counts likely undercount true executions and overcount per-execution time. "
            "One inspected payroll segment blended 5132 payroll text with 5134 "
            "inventory-adjustment text after an undetected mid-segment navigation.",
            "The 保留 (hold) path was never observed in any inspected segment.",
            "The case IDs regex-matched to this segment (INV-2026-79xx) were dashboard "
            "list-view noise, NOT the record processed. The real key is 管理ID + 社員ID. "
            "Case-ID evidence is present in only 23% of this family's executions.",
            "The 参照 note shows approval authority varies by requester type "
            "(申請者区分 / 承認権限) without revealing the thresholds, so the real policy "
            "has branches that were never visible. The amount limit used here is an "
            "explicit prototype value, not a company rule.",
        ],
    ),
)
