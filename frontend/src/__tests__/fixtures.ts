/**
 * Mock data for the frontend stage.
 *
 * GROUNDING RULES (carried from Phase 1/2 discipline):
 *  - Business records mirror `backend/data/leave_requests.json` exactly — same
 *    ids, names, request types, dates, departments and provenance. When the API
 *    layer is switched to live FastAPI calls these rows are simply replaced.
 *  - Workflow evidence numbers (23 executions / 18.63 min, etc.) are the REAL
 *    Phase 2 measurements from `phase2/results/automation_candidates.csv`.
 *  - Everything else — job states, run history, aggregate counters — is
 *    fabricated UI state for this stage and is labelled as demo data in the UI.
 *    No agent has run yet, so no number here is a real performance claim.
 */

import type {
  AgentDecision,
  AutomationJob,
  ExecutionResult,
  LeaveRequest,
  PayrollItem,
  PrototypeMetrics,
  QueueStage,
  QueueTask,
  RunHistoryEntry,
  WorkflowDefinition,
} from '@/types'

/** Fixed clock so the demo renders identically on every load. */
export const DEMO_NOW = new Date('2026-09-17T14:02:30+09:00')

const minsAgo = (m: number) => new Date(DEMO_NOW.getTime() - m * 60_000).toISOString()

/* ========================================================================== */
/* Business records — mirrors backend/data/leave_requests.json                */
/* ========================================================================== */

export const leaveRequests: LeaveRequest[] = [
  {
    record_id: 'P2-07048822-006',
    status: '申請中',
    employee_id: 'E2001',
    employee_name: '青木 拓也',
    request_type: '代休申請',
    request_date: '2026-07-13',
    department: '営業部',
    prior_approval_required: true,
    prior_approval_obtained: null,
    comment: null,
    provenance: 'dataset_b_observed',
    evidence_note:
      'Detail panel fully confirmed by screenshot and the 承認 action on this record was the clean 4.4s execution in segment ses_20260701-180923-NEELA9BAF::seg013.',
  },
  {
    record_id: 'P2-07048822-007', status: '申請中', employee_id: 'E2009', employee_name: '坂本 裕二',
    request_type: '半日有給申請', request_date: '2026-07-08', department: '人事部',
    prior_approval_required: null, prior_approval_obtained: null, comment: null,
    provenance: 'dataset_b_list_observed',
    evidence_note: 'Row visible in list screenshot; detail panel never opened.',
  },
  {
    record_id: 'P2-07048822-008', status: '申請中', employee_id: 'E2003', employee_name: '上野 大樹',
    request_type: '年次有給休暇', request_date: '2026-07-16', department: '経理部',
    prior_approval_required: null, prior_approval_obtained: null, comment: null,
    provenance: 'dataset_b_list_observed',
    evidence_note: 'Row visible in list screenshot; detail panel never opened.',
  },
  {
    record_id: 'P2-07048822-009', status: '申請中', employee_id: 'E2006', employee_name: '菊池 理恵',
    request_type: '代休申請', request_date: '2026-07-13', department: '営業部',
    prior_approval_required: null, prior_approval_obtained: null, comment: null,
    provenance: 'dataset_b_list_observed',
    evidence_note: 'Row visible in list screenshot; detail panel never opened.',
  },
  {
    record_id: 'P2-07048822-010', status: '申請中', employee_id: 'E2007', employee_name: '桐島 涼介',
    request_type: 'フレックス変更申請', request_date: '2026-07-11', department: '開発部',
    prior_approval_required: null, prior_approval_obtained: null, comment: null,
    provenance: 'dataset_b_list_observed',
    evidence_note: 'Row visible in list screenshot; detail panel never opened.',
  },
  {
    record_id: 'P2-07048822-011', status: '申請中', employee_id: 'E2005', employee_name: '岡田 智也',
    request_type: 'フレックス変更申請', request_date: '2026-07-13', department: '物流部',
    prior_approval_required: null, prior_approval_obtained: null, comment: null,
    provenance: 'dataset_b_list_observed',
    evidence_note: 'Row visible in list screenshot; detail panel never opened.',
  },
  {
    record_id: 'P2-07048822-012', status: '申請中', employee_id: 'E2003', employee_name: '上野 大樹',
    request_type: '代休申請', request_date: '2026-07-16', department: '経理部',
    prior_approval_required: null, prior_approval_obtained: null, comment: null,
    provenance: 'dataset_b_list_observed',
    evidence_note: 'Row visible in list screenshot; detail panel never opened.',
  },
  {
    record_id: 'DEMO-LV-001', status: '申請中', employee_id: 'E2101', employee_name: '佐々木 亮',
    request_type: '代休申請', request_date: '2026-07-21', department: '営業部',
    prior_approval_required: true, prior_approval_obtained: true, comment: null,
    provenance: 'synthetic_demo', evidence_note: null,
  },
  {
    record_id: 'DEMO-LV-002', status: '申請中', employee_id: 'E2102', employee_name: '小林 美咲',
    request_type: '半日有給申請', request_date: '2026-07-22', department: '人事部',
    prior_approval_required: false, prior_approval_obtained: null, comment: null,
    provenance: 'synthetic_demo', evidence_note: null,
  },
  {
    record_id: 'DEMO-LV-003', status: '申請中', employee_id: 'E2103', employee_name: '中村 翔太',
    request_type: 'フレックス変更申請', request_date: '2026-07-23', department: '開発部',
    prior_approval_required: false, prior_approval_obtained: null, comment: null,
    provenance: 'synthetic_demo', evidence_note: null,
  },
  {
    record_id: 'DEMO-LV-004', status: '申請中', employee_id: 'E2104', employee_name: '高橋 直美',
    request_type: '代休申請', request_date: '2026-07-24', department: '経理部',
    prior_approval_required: true, prior_approval_obtained: true, comment: '前月の休日出勤分',
    provenance: 'synthetic_demo', evidence_note: null,
  },
  {
    record_id: 'DEMO-LV-005', status: '申請中', employee_id: 'E2105', employee_name: '井上 健',
    request_type: '代休申請', request_date: '2026-07-27', department: '物流部',
    prior_approval_required: true, prior_approval_obtained: false, comment: null,
    provenance: 'synthetic_demo', evidence_note: null,
  },
  {
    record_id: 'DEMO-LV-006', status: '申請中', employee_id: 'E2106', employee_name: '森田 彩',
    request_type: '年次有給休暇', request_date: '2026-07-28', department: '営業部',
    prior_approval_required: false, prior_approval_obtained: null, comment: null,
    provenance: 'synthetic_demo', evidence_note: null,
  },
  {
    record_id: 'DEMO-LV-007', status: '申請中', employee_id: 'E2107', employee_name: '山口 拓海',
    request_type: '特別休暇申請', request_date: '2026-07-29', department: '管理部',
    prior_approval_required: null, prior_approval_obtained: null, comment: '慶弔のため',
    provenance: 'synthetic_demo', evidence_note: null,
  },
  {
    record_id: 'DEMO-LV-008', status: '申請中', employee_id: null, employee_name: '渡辺 さくら',
    request_type: '代休申請', request_date: '2026-07-30', department: null,
    prior_approval_required: true, prior_approval_obtained: true, comment: null,
    provenance: 'synthetic_demo', evidence_note: null,
  },
  {
    record_id: 'DEMO-LV-009', status: '申請中', employee_id: 'E2109', employee_name: '藤田 大輔',
    request_type: '代休申請', request_date: null, department: '開発部',
    prior_approval_required: true, prior_approval_obtained: true, comment: null,
    provenance: 'synthetic_demo', evidence_note: null,
  },
  {
    record_id: 'DEMO-LV-010', status: '承認済み', employee_id: 'E2110', employee_name: '松本 香織',
    request_type: '代休申請', request_date: '2026-07-31', department: '人事部',
    prior_approval_required: true, prior_approval_obtained: true, comment: '承認済み（デモ用）',
    provenance: 'synthetic_demo', evidence_note: null,
  },
]

export const payrollItems: PayrollItem[] = [
  {
    record_id: 'DEMO-PAY-REVIEW', status: '未処理', employee_id: 'E2204',
    employee_name: '黒田 直樹', category: '研修費', amount: '148500',
    policy_reference: '申請者区分：manager　承認権限：本部長',
    comment: null, provenance: 'synthetic_demo', evidence_note: null,
  },
  {
    record_id: 'P1-07046967-001', status: '未処理', employee_id: 'E2011', employee_name: '清水 祥平',
    category: '研修費', amount: '25213', policy_reference: '申請者区分：regular　承認権限：部門長',
    comment: null, provenance: 'dataset_b_observed',
    evidence_note: 'Detail panel confirmed by screenshot; clean 11.7s execution in segment ses_20260701-190250-NEELA9BAF::seg002.',
  },
  {
    record_id: 'P4-07046967-009', status: '未処理', employee_id: 'E2015', employee_name: '遠山 健一',
    category: '役職手当廃止', amount: '16424', policy_reference: null, comment: null,
    provenance: 'dataset_b_list_observed', evidence_note: 'Row visible in list screenshot.',
  },
  {
    record_id: 'P4-07046967-012', status: '未処理', employee_id: 'E2012', employee_name: '竹内 彩子',
    category: '役職手当新設', amount: '25158', policy_reference: null, comment: null,
    provenance: 'dataset_b_list_observed', evidence_note: 'Row visible in list screenshot.',
  },
  {
    record_id: 'DEMO-PAY-001', status: '未処理', employee_id: 'E2201', employee_name: '大野 真一',
    category: '研修費', amount: '9800', policy_reference: '申請者区分：regular　承認権限：部門長',
    comment: null, provenance: 'synthetic_demo', evidence_note: null,
  },
]

/* ========================================================================== */
/* Workflow definitions — evidence numbers are REAL Phase 2 measurements      */
/* ========================================================================== */

export const workflows: WorkflowDefinition[] = [
  {
    workflow: 'LEAVE_APPROVAL',
    name: 'Leave Approval',
    description:
      'Review one pending leave/attendance request against an explicit prototype policy and either approve it, return it, or escalate it to a human.',
    implemented: true,
    record_model: 'LeaveRequest',
    policy_key: 'leave_approval',
    steps: [
      { step_id: 'load_request', name: 'Load pending request', description: 'Fetch one pending leave request from the queue.', state: 'LOADING', automated: true },
      { step_id: 'validate_request', name: 'Validate required information', description: 'Check the record carries every field the policy needs.', state: 'VALIDATING', automated: true },
      { step_id: 'analyze', name: 'Analyze relevant fields', description: 'Extract the decision-relevant fields incl. the 事前承認要否 flag.', state: 'ANALYZING', automated: true },
      { step_id: 'policy_check', name: 'Evaluate configured policy', description: 'Apply the explicit prototype policy and produce a structured decision.', state: 'POLICY_CHECK', automated: true },
      { step_id: 'human_review', name: 'Human review', description: 'A person resolves records the policy could not decide.', state: 'HUMAN_REVIEW', automated: false },
      { step_id: 'execute', name: 'Execute decision in the HR system', description: 'Deterministically open the record and click the decided control.', state: 'EXECUTING', automated: true },
      { step_id: 'verify', name: 'Verify resulting status', description: 'Re-read the status and confirm it actually changed.', state: 'VERIFYING', automated: true },
    ],
    supported_decisions: ['APPROVE', 'REJECT', 'REVIEW'],
    execution_actions: [
      { decision: 'APPROVE', action: 'APPROVE_LEAVE', ui_target_label: '承認', auto_executable: true, rationale: 'The approve path was directly observed end to end in Dataset B.' },
      { decision: 'REJECT', action: 'REJECT_LEAVE', ui_target_label: '差戻し', auto_executable: false, rationale: 'The 差戻し button was NEVER observed being used. The prototype does not auto-execute it.' },
    ],
    verification: {
      method: 'Re-read the record status after submitting and compare against the expected label.',
      status_before: '申請中',
      expected_status_after: { APPROVE: '承認済み', REJECT: '差戻し' },
      expected_status_observed_in_dataset_b: false,
      note: 'PROTOTYPE ASSUMPTION — no approved record was captured in Dataset B, so post-action labels are assumed.',
    },
    evidence: {
      dataset: 'dataset_b',
      process_type_id: 'B-127.0.0.1_5132_leave-applications',
      observed_executions: 23,
      observed_minutes: 18.63,
      observed_workers: 3,
      observed_sessions: 6,
      family_median_duration_seconds: 40.83,
      clean_instance_segment_id: 'ses_20260701-180923-NEELA9BAF::seg013',
      clean_instance_duration_seconds: 4.365,
      clean_instance_event_count: 17,
      phase2_confidence_level: 'High',
      visually_confirmed: true,
      source_documents: ['phase2_summary.md', 'visual_audit.md', 'step3_prototype_spec.md'],
      caveats: [
        'Only 30.5% of Phase 2 segments were single-app/single-route.',
        'The reject (差戻し) path was never observed in any inspected segment.',
        'Dataset B never revealed the real approval policy, only that an action was taken.',
      ],
    },
  },
  {
    workflow: 'PAYROLL_CONFIRMATION',
    name: 'Payroll Confirmation',
    description:
      'Review one pending payroll/expense line item against an explicit prototype policy and either confirm it, hold it, or escalate it to a human.',
    implemented: true,
    record_model: 'PayrollItem',
    policy_key: 'payroll_confirmation',
    steps: [
      { step_id: 'load_item', name: 'Load pending payroll item', description: 'Fetch one pending line item from the expense/salary queue.', state: 'LOADING', automated: true },
      { step_id: 'validate_item', name: 'Validate required information', description: 'Check the record carries every field the policy needs.', state: 'VALIDATING', automated: true },
      { step_id: 'analyze', name: 'Analyze relevant fields', description: 'Extract the decision-relevant fields: category, amount, and the 参照 policy-reference note.', state: 'ANALYZING', automated: true },
      { step_id: 'policy_check', name: 'Evaluate configured policy', description: 'Apply the explicit prototype policy and produce a structured decision.', state: 'POLICY_CHECK', automated: true },
      { step_id: 'human_review', name: 'Human review', description: 'A person resolves records the policy could not decide.', state: 'HUMAN_REVIEW', automated: false },
      { step_id: 'execute', name: 'Execute decision in the payroll system', description: 'Deterministically open the record and click the decided control.', state: 'EXECUTING', automated: true },
      { step_id: 'verify', name: 'Verify resulting status', description: 'Re-read the status from the queue screen and confirm it actually changed.', state: 'VERIFYING', automated: true },
    ],
    supported_decisions: ['APPROVE', 'REJECT', 'REVIEW'],
    execution_actions: [
      {
        decision: 'APPROVE',
        action: 'CONFIRM_PAYROLL',
        ui_target_label: '登録確定',
        auto_executable: true,
        rationale:
          'The confirm path was directly observed end to end in Dataset B (segment ses_20260701-190250-NEELA9BAF::seg002, record P1-07046967-001).',
      },
      {
        decision: 'REJECT',
        action: 'HOLD_PAYROLL',
        ui_target_label: '保留',
        auto_executable: false,
        rationale:
          'The 保留 (hold) button exists in the UI but was NEVER observed being used. Such records go to human review.',
      },
    ],
    verification: {
      method:
        "Re-read the item's status from the queue screen after submitting and compare it against the expected post-action label.",
      status_before: '未処理',
      expected_status_after: { APPROVE: '登録確定済み', REJECT: '保留' },
      expected_status_observed_in_dataset_b: false,
      note: 'PROTOTYPE ASSUMPTION. The post-action status labels are derived from the button labels rather than observed.',
    },
    evidence: {
      dataset: 'dataset_b',
      process_type_id: 'B-127.0.0.1_5132_payroll-items',
      observed_executions: 39,
      observed_minutes: 30.16,
      observed_workers: 4,
      observed_sessions: 10,
      family_median_duration_seconds: 28.82,
      clean_instance_segment_id: 'ses_20260701-190250-NEELA9BAF::seg002',
      clean_instance_duration_seconds: 11.686,
      clean_instance_event_count: 24,
      phase2_confidence_level: 'High',
      visually_confirmed: true,
      source_documents: ['phase2_summary.md', 'visual_audit.md', 'step3_prototype_spec.md'],
      caveats: [
        'Regex-matched case ids on the observed segment were list-view noise, not the record processed.',
        'The 保留 (hold) path was never observed being used.',
      ],
    },
  },
]

/* ========================================================================== */
/* Policy checks / decisions                                                  */
/* ========================================================================== */

const POLICY_VERSION = 'leave-approval-prototype-v1'

function approveDecision(confidence: number, note: string): AgentDecision {
  return {
    decision: 'APPROVE',
    reason: note,
    confidence,
    human_review_required: false,
    ambiguity_type: null,
    policy_version: POLICY_VERSION,
    decided_by: 'llm+policy_guard',
    decided_at: minsAgo(3),
    policy_checks: [
      { check_id: 'status_actionable', description: 'Record status is in the actionable set (申請中)', passed: true, detail: 'Status 申請中 is actionable.', source: 'Record field' },
      { check_id: 'required_fields', description: 'All policy-required fields are present', passed: true, detail: 'employee_id, employee_name, request_type, request_date, department all present.', source: 'Record validation' },
      { check_id: 'request_type_allowed', description: 'Request type is auto-approvable under the prototype policy', passed: true, detail: 'Type is in allowed_request_types — observed being approved in Dataset B.', source: 'policies.json' },
      { check_id: 'prior_approval', description: '事前承認要否 condition satisfied', passed: true, detail: 'Prior approval required and recorded as obtained.', source: 'Record field + policy rule' },
    ],
  }
}

function reviewDecision(
  reason: string,
  ambiguity: AgentDecision['ambiguity_type'],
  confidence: number,
  checks: AgentDecision['policy_checks'],
): AgentDecision {
  return {
    decision: 'REVIEW',
    reason,
    confidence,
    human_review_required: true,
    ambiguity_type: ambiguity,
    policy_version: POLICY_VERSION,
    decided_by: 'llm+policy_guard',
    decided_at: minsAgo(6),
    policy_checks: checks,
  }
}

/* ========================================================================== */
/* Jobs                                                                       */
/* ========================================================================== */

const byId = (id: string) => leaveRequests.find((r) => r.record_id === id)!

const executionFor = (
  recordId: string,
  opts: { complete: boolean; verified: boolean; durationS?: number },
): ExecutionResult => {
  const names = [
    'Open leave-applications queue',
    'Locate record row',
    'Open detail panel',
    'Read current status',
    'Click 承認',
    'Submit',
    'Re-read status',
  ]
  const doneCount = opts.complete ? names.length : 4
  return {
    action: 'APPROVE_LEAVE',
    workflow: 'LEAVE_APPROVAL',
    record_id: recordId,
    success: opts.complete,
    steps_completed: names.map((name, i) => ({
      name,
      completed: i < doneCount,
      detail:
        i === 3 ? 'Status read as 申請中'
        : i === 4 ? 'Clicked the 承認 control'
        : i === 6 && opts.complete ? 'Status read as 承認済み'
        : null,
      error: null,
      at: i < doneCount ? minsAgo(2 - i * 0.1) : null,
    })),
    verification_status: opts.complete ? (opts.verified ? 'VERIFIED' : 'FAILED') : 'NOT_ATTEMPTED',
    status_before: '申請中',
    status_after: opts.complete ? '承認済み' : null,
    error: null,
    started_at: minsAgo(2),
    finished_at: opts.complete ? minsAgo(1.6) : null,
    duration_seconds: opts.complete ? (opts.durationS ?? 3.8) : null,
    executed_by: 'agent',
  }
}

export const jobs: AutomationJob[] = [
  /* --- the record that escalates because the evidence genuinely runs out --- */
  {
    job_id: 'JOB-2041',
    workflow: 'LEAVE_APPROVAL',
    state: 'HUMAN_REVIEW',
    record: byId('P2-07048822-006'),
    decision: reviewDecision(
      'Prior approval is required for this request, but whether it was obtained cannot be established from the record. The prototype policy routes this to a human rather than assuming either way.',
      'MISSING_REQUIRED_DATA',
      0.42,
      [
        { check_id: 'status_actionable', description: 'Record status is in the actionable set (申請中)', passed: true, detail: 'Status 申請中 is actionable.', source: 'Record field' },
        { check_id: 'required_fields', description: 'All policy-required fields are present', passed: true, detail: 'All five required fields present.', source: 'Record validation' },
        { check_id: 'request_type_allowed', description: 'Request type is auto-approvable under the prototype policy', passed: true, detail: '代休申請 was directly observed being approved in Dataset B.', source: 'policies.json' },
        { check_id: 'prior_approval', description: '事前承認要否 condition satisfied', passed: null, detail: 'Required = true, but obtained = unknown. Dataset B showed whether prior approval was REQUIRED, never whether it was OBTAINED.', source: 'Record field + policy rule' },
      ],
    ),
    human_decision: null,
    execution: null,
    state_history: [
      { from_state: 'START', to_state: 'LOADING', at: minsAgo(8), note: null },
      { from_state: 'LOADING', to_state: 'VALIDATING', at: minsAgo(8), note: '5/5 required fields present' },
      { from_state: 'VALIDATING', to_state: 'ANALYZING', at: minsAgo(7), note: null },
      { from_state: 'ANALYZING', to_state: 'POLICY_CHECK', at: minsAgo(7), note: null },
      { from_state: 'POLICY_CHECK', to_state: 'HUMAN_REVIEW', at: minsAgo(6), note: 'Gate 4 not evaluable — escalated' },
    ],
    error: null,
    created_at: minsAgo(8),
    updated_at: minsAgo(6),
  },
  /* --- clean auto-approval sitting at the policy gate, ready to execute ---- */
  {
    job_id: 'JOB-2042',
    workflow: 'LEAVE_APPROVAL',
    state: 'POLICY_CHECK',
    record: byId('DEMO-LV-001'),
    decision: approveDecision(0.96, 'All four policy gates cleared. 代休申請 is auto-approvable and prior approval is recorded as obtained.'),
    human_decision: null,
    execution: null,
    state_history: [
      { from_state: 'START', to_state: 'LOADING', at: minsAgo(4), note: null },
      { from_state: 'LOADING', to_state: 'VALIDATING', at: minsAgo(4), note: null },
      { from_state: 'VALIDATING', to_state: 'ANALYZING', at: minsAgo(3), note: null },
      { from_state: 'ANALYZING', to_state: 'POLICY_CHECK', at: minsAgo(3), note: '4/4 gates cleared' },
    ],
    error: null,
    created_at: minsAgo(4),
    updated_at: minsAgo(3),
  },
  /* --- mid-execution --------------------------------------------------- */
  {
    job_id: 'JOB-2043',
    workflow: 'LEAVE_APPROVAL',
    state: 'EXECUTING',
    record: byId('DEMO-LV-004'),
    decision: approveDecision(0.94, 'All four policy gates cleared.'),
    human_decision: null,
    execution: executionFor('DEMO-LV-004', { complete: false, verified: false }),
    state_history: [
      { from_state: 'START', to_state: 'LOADING', at: minsAgo(3), note: null },
      { from_state: 'LOADING', to_state: 'VALIDATING', at: minsAgo(3), note: null },
      { from_state: 'VALIDATING', to_state: 'ANALYZING', at: minsAgo(2.6), note: null },
      { from_state: 'ANALYZING', to_state: 'POLICY_CHECK', at: minsAgo(2.4), note: null },
      { from_state: 'POLICY_CHECK', to_state: 'EXECUTING', at: minsAgo(2), note: 'Decision APPROVE → deterministic execution' },
    ],
    error: null,
    created_at: minsAgo(3),
    updated_at: minsAgo(2),
  },
  /* --- completed & verified --------------------------------------------- */
  {
    job_id: 'JOB-2039',
    workflow: 'LEAVE_APPROVAL',
    state: 'COMPLETED',
    record: byId('DEMO-LV-002'),
    decision: approveDecision(0.93, 'Prior approval not required for this request type; all other gates cleared.'),
    human_decision: null,
    execution: executionFor('DEMO-LV-002', { complete: true, verified: true, durationS: 3.4 }),
    state_history: [
      { from_state: 'POLICY_CHECK', to_state: 'EXECUTING', at: minsAgo(16), note: null },
      { from_state: 'EXECUTING', to_state: 'VERIFYING', at: minsAgo(15), note: null },
      { from_state: 'VERIFYING', to_state: 'COMPLETED', at: minsAgo(15), note: '申請中 → 承認済み confirmed' },
    ],
    error: null,
    created_at: minsAgo(18),
    updated_at: minsAgo(15),
  },
  {
    job_id: 'JOB-2040',
    workflow: 'LEAVE_APPROVAL',
    state: 'COMPLETED',
    record: byId('DEMO-LV-003'),
    decision: approveDecision(0.91, 'Prior approval not required; all gates cleared.'),
    human_decision: null,
    execution: executionFor('DEMO-LV-003', { complete: true, verified: true, durationS: 4.1 }),
    state_history: [
      { from_state: 'POLICY_CHECK', to_state: 'EXECUTING', at: minsAgo(12), note: null },
      { from_state: 'EXECUTING', to_state: 'VERIFYING', at: minsAgo(11), note: null },
      { from_state: 'VERIFYING', to_state: 'COMPLETED', at: minsAgo(11), note: '申請中 → 承認済み confirmed' },
    ],
    error: null,
    created_at: minsAgo(13),
    updated_at: minsAgo(11),
  },
  /* --- other escalations ------------------------------------------------ */
  {
    job_id: 'JOB-2044',
    workflow: 'LEAVE_APPROVAL',
    state: 'HUMAN_REVIEW',
    record: byId('DEMO-LV-005'),
    decision: reviewDecision(
      'Prior approval is required for this request and is explicitly recorded as NOT obtained. The prototype policy does not auto-reject, so this needs a human determination.',
      'ACTION_NOT_AUTO_EXECUTABLE',
      0.71,
      [
        { check_id: 'status_actionable', description: 'Record status is in the actionable set (申請中)', passed: true, detail: 'Status 申請中 is actionable.', source: 'Record field' },
        { check_id: 'required_fields', description: 'All policy-required fields are present', passed: true, detail: 'All five required fields present.', source: 'Record validation' },
        { check_id: 'request_type_allowed', description: 'Request type is auto-approvable', passed: true, detail: '代休申請 is in allowed_request_types.', source: 'policies.json' },
        { check_id: 'prior_approval', description: '事前承認要否 condition satisfied', passed: false, detail: 'Required = true, obtained = false. Rejection is not auto-executable (差戻し never observed), so this escalates.', source: 'Record field + policy rule' },
      ],
    ),
    human_decision: null,
    execution: null,
    state_history: [
      { from_state: 'ANALYZING', to_state: 'POLICY_CHECK', at: minsAgo(22), note: null },
      { from_state: 'POLICY_CHECK', to_state: 'HUMAN_REVIEW', at: minsAgo(21), note: 'Gate 4 failed; auto-rejection disabled by policy' },
    ],
    error: null,
    created_at: minsAgo(24),
    updated_at: minsAgo(21),
  },
  {
    job_id: 'JOB-2045',
    workflow: 'LEAVE_APPROVAL',
    state: 'HUMAN_REVIEW',
    record: byId('DEMO-LV-007'),
    decision: reviewDecision(
      '特別休暇申請 is not covered by the prototype policy — it was never observed being approved in Dataset B, so it is not in allowed_request_types.',
      'POLICY_NOT_COVERED',
      0.38,
      [
        { check_id: 'status_actionable', description: 'Record status is in the actionable set (申請中)', passed: true, detail: 'Status 申請中 is actionable.', source: 'Record field' },
        { check_id: 'required_fields', description: 'All policy-required fields are present', passed: true, detail: 'All five required fields present.', source: 'Record validation' },
        { check_id: 'request_type_allowed', description: 'Request type is auto-approvable', passed: false, detail: '特別休暇申請 is not in allowed_request_types and has no observed precedent.', source: 'policies.json' },
        { check_id: 'prior_approval', description: '事前承認要否 condition satisfied', passed: null, detail: 'Not evaluated — earlier gate already routed this to review.', source: 'Record field + policy rule' },
      ],
    ),
    human_decision: null,
    execution: null,
    state_history: [
      { from_state: 'ANALYZING', to_state: 'POLICY_CHECK', at: minsAgo(34), note: null },
      { from_state: 'POLICY_CHECK', to_state: 'HUMAN_REVIEW', at: minsAgo(33), note: 'Request type not covered by policy' },
    ],
    error: null,
    created_at: minsAgo(36),
    updated_at: minsAgo(33),
  },
  /* --- incomplete record, caught at validation -------------------------- */
  {
    job_id: 'JOB-2046',
    workflow: 'LEAVE_APPROVAL',
    state: 'HUMAN_REVIEW',
    record: byId('DEMO-LV-008'),
    decision: reviewDecision(
      'Record is missing employee_id and department. Incomplete records are escalated rather than failed, per the prototype policy.',
      'MISSING_REQUIRED_DATA',
      0.2,
      [
        { check_id: 'status_actionable', description: 'Record status is in the actionable set (申請中)', passed: true, detail: 'Status 申請中 is actionable.', source: 'Record field' },
        { check_id: 'required_fields', description: 'All policy-required fields are present', passed: false, detail: 'Missing: employee_id, department.', source: 'Record validation' },
        { check_id: 'request_type_allowed', description: 'Request type is auto-approvable', passed: null, detail: 'Not evaluated.', source: 'policies.json' },
        { check_id: 'prior_approval', description: '事前承認要否 condition satisfied', passed: null, detail: 'Not evaluated.', source: 'Record field + policy rule' },
      ],
    ),
    human_decision: null,
    execution: null,
    state_history: [
      { from_state: 'LOADING', to_state: 'VALIDATING', at: minsAgo(45), note: null },
      { from_state: 'VALIDATING', to_state: 'HUMAN_REVIEW', at: minsAgo(44), note: '2 required fields missing' },
    ],
    error: null,
    created_at: minsAgo(46),
    updated_at: minsAgo(44),
  },
  /* --- one failed verification ------------------------------------------ */
  {
    job_id: 'JOB-2038',
    workflow: 'LEAVE_APPROVAL',
    state: 'FAILED',
    record: byId('DEMO-LV-009'),
    decision: approveDecision(0.88, 'Gates cleared on the fields present.'),
    human_decision: null,
    execution: {
      ...executionFor('DEMO-LV-009', { complete: true, verified: false, durationS: 6.2 }),
      success: false,
      verification_status: 'FAILED',
      status_after: '申請中',
      error: 'Status did not change after submit — record still reads 申請中.',
    },
    state_history: [
      { from_state: 'POLICY_CHECK', to_state: 'EXECUTING', at: minsAgo(52), note: null },
      { from_state: 'EXECUTING', to_state: 'VERIFYING', at: minsAgo(51), note: null },
      { from_state: 'VERIFYING', to_state: 'FAILED', at: minsAgo(51), note: 'Status unchanged after submit' },
    ],
    error: 'Verification failed: status unchanged after submit.',
    created_at: minsAgo(54),
    updated_at: minsAgo(51),
  },
]

/* ========================================================================== */
/* Queue                                                                      */
/* ========================================================================== */

const STAGE_BY_STATE: Record<string, QueueStage> = {
  START: 'Queued',
  LOADING: 'Queued',
  VALIDATING: 'Agent Evaluating',
  ANALYZING: 'Agent Evaluating',
  POLICY_CHECK: 'Agent Evaluating',
  HUMAN_REVIEW: 'Pending Human Sign-off',
  EXECUTING: 'Executing',
  VERIFYING: 'Verifying',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
}

/** Mirrors `detailLine` in services/api.ts, so the fixtures exercise real copy. */
function fixtureDetailLine(rec: LeaveRequest): string {
  const gaps: string[] = []
  if (!rec.employee_id) gaps.push('employee_id missing')
  if (!rec.request_date) gaps.push('date missing')
  if (!rec.department) gaps.push('department missing')
  if (gaps.length) return gaps.join(' · ')
  return [rec.request_type, rec.request_date, rec.department].filter(Boolean).join(' · ')
}


function taskFromJob(job: AutomationJob, index: number): QueueTask {
  const rec = job.record as LeaveRequest
  return {
    task_id: `#LV-${8900 + index}`,
    job_id: job.job_id,
    workflow: job.workflow,
    record: job.record,
    state: job.state,
    stage: STAGE_BY_STATE[job.state],
    decision: job.decision?.decision ?? null,
    confidence: job.decision?.confidence ?? null,
    submitted_at: job.created_at,
    detail_line: fixtureDetailLine(rec),
    duration_label: '—',
    duration_seconds: null,
  }
}

/** Jobs already in flight, plus untouched records still waiting in the queue. */
export const queueTasks: QueueTask[] = [
  ...jobs.map(taskFromJob),
  ...leaveRequests
    .filter(
      (r) =>
        r.status === '申請中' &&
        !jobs.some((j) => j.record.record_id === r.record_id),
    )
    .map((r, i): QueueTask => ({
      task_id: `#LV-${8950 + i}`,
      job_id: `JOB-QUEUED-${i}`,
      workflow: 'LEAVE_APPROVAL',
      record: r,
      state: 'START',
      stage: 'Queued',
      decision: null,
      confidence: null,
      submitted_at: minsAgo(60 + i * 7),
      detail_line: fixtureDetailLine(r),
      duration_label: '—',
      duration_seconds: null,
    })),
]

/* ========================================================================== */
/* Run history                                                                */
/* ========================================================================== */

const SYSTEMS = ['HR人事給与システム', 'Policy Config', 'Playwright']

export const runHistory: RunHistoryEntry[] = [
  ...jobs
    .filter((j) => j.state === 'COMPLETED' || j.state === 'FAILED')
    .map((j, i): RunHistoryEntry => ({
      run_id: `RUN-${4120 + i}`,
      job_id: j.job_id,
      timestamp: j.updated_at,
      workflow: j.workflow,
      subject: (j.record as LeaveRequest).employee_name ?? j.record.record_id,
      subject_detail: `${(j.record as LeaveRequest).request_type ?? '—'} · ${j.record.record_id}`,
      decision: j.decision?.decision ?? 'REVIEW',
      human_overridden: false,
      verification_status: j.execution?.verification_status ?? 'NOT_ATTEMPTED',
      duration_ms: Math.round((j.execution?.duration_seconds ?? 0) * 1000),
      systems_touched: SYSTEMS,
    })),
  ...Array.from({ length: 14 }, (_, i): RunHistoryEntry => {
    const rec = leaveRequests[(i + 3) % leaveRequests.length]
    const failed = i === 4
    const overridden = i === 2 || i === 9
    return {
      run_id: `RUN-${4100 + i}`,
      job_id: `JOB-19${60 + i}`,
      timestamp: minsAgo(70 + i * 23),
      workflow: i % 5 === 0 ? 'PAYROLL_CONFIRMATION' : 'LEAVE_APPROVAL',
      subject: rec.employee_name ?? rec.record_id,
      subject_detail: `${rec.request_type ?? '—'} · ${rec.record_id}`,
      decision: overridden ? 'APPROVE' : failed ? 'REVIEW' : 'APPROVE',
      human_overridden: overridden,
      verification_status: failed ? 'FAILED' : 'VERIFIED',
      duration_ms: 3200 + ((i * 431) % 2600),
      systems_touched: SYSTEMS,
    }
  }),
]

/* ========================================================================== */
/* Derived metrics — computed from the mock jobs so the numbers agree         */
/* ========================================================================== */

export function computeMetrics() {
  const total = jobs.length
  const completed = jobs.filter((j) => j.state === 'COMPLETED').length
  const failed = jobs.filter((j) => j.state === 'FAILED').length
  const review = jobs.filter((j) => j.state === 'HUMAN_REVIEW').length
  const inFlight = jobs.filter(
    (j) => !['COMPLETED', 'FAILED', 'HUMAN_REVIEW'].includes(j.state),
  ).length
  const autoDecided = jobs.filter((j) => j.decision && !j.decision.human_review_required).length

  const durations = jobs
    .map((j) => j.execution?.duration_seconds)
    .filter((d): d is number => typeof d === 'number' && d > 0)
  const avgDuration = durations.length
    ? durations.reduce((a, b) => a + b, 0) / durations.length
    : 0

  const verified = jobs.filter((j) => j.execution?.verification_status === 'VERIFIED').length
  const attempted = jobs.filter(
    (j) => j.execution && j.execution.verification_status !== 'NOT_ATTEMPTED',
  ).length

  return {
    totalJobs: total,
    completed,
    failed,
    humanReview: review,
    inFlight,
    queued: queueTasks.filter((t) => t.stage === 'Queued').length,
    autonomousRate: total ? autoDecided / total : 0,
    verificationRate: attempted ? verified / attempted : 0,
    avgExecutionSeconds: avgDuration,
    pendingRecords: leaveRequests.filter((r) => r.status === '申請中').length,
    llmDecisions: jobs.filter((j) => j.decision?.decided_by === 'llm+policy_guard').length,
    // Provenance counts across BOTH queues, mirroring services/api.ts.
    totalRecords: leaveRequests.length + payrollItems.length,
    observedRecords: [...leaveRequests, ...payrollItems].filter(
      (r) => r.provenance === 'dataset_b_observed',
    ).length,
    listObservedRecords: [...leaveRequests, ...payrollItems].filter(
      (r) => r.provenance === 'dataset_b_list_observed',
    ).length,
    syntheticRecords: [...leaveRequests, ...payrollItems].filter(
      (r) => r.provenance === 'synthetic_demo',
    ).length,
  }
}

/** Decision split across every job that reached a decision. */
export function decisionDistribution() {
  const decided = jobs.filter((j) => j.decision)
  const approve = decided.filter((j) => j.decision!.decision === 'APPROVE').length
  const review = decided.filter((j) => j.decision!.decision === 'REVIEW').length
  const reject = decided.filter((j) => j.decision!.decision === 'REJECT').length
  return { approve, review, reject, total: decided.length }
}

/** Connected/target systems — the real pieces of this architecture. */
export const systemConnectors = [
  { name: 'HR人事給与システム', detail: 'Target UI · 127.0.0.1:5132', status: 'planned' as const },
  { name: 'FastAPI backend', detail: 'localhost:8000 · foundation live', status: 'connected' as const },
  { name: 'Policy config', detail: 'policies.json · prototype-v1', status: 'connected' as const },
  { name: 'Playwright executor', detail: 'Deterministic browser actions', status: 'planned' as const },
]

/** 30-day throughput series for the audit chart (demo data). */
export const throughputSeries = Array.from({ length: 30 }, (_, i) => {
  const auto = 18 + Math.round(9 * Math.sin(i / 3.1) + (i % 4) * 1.6)
  const human = 2 + ((i * 7) % 4)
  return { day: i, auto, human }
})

/* ========================================================================== */
/* Payroll Confirmation jobs - workflow #2                                    */
/* ========================================================================== */

const PAYROLL_POLICY = 'payroll-confirmation-prototype-v1'

function payrollGates(amountPassed: boolean, amountDetail: string) {
  return [
    { check_id: 'status_actionable', description: 'Status must be \u672a\u51e6\u7406', passed: true, detail: 'Status is \u672a\u51e6\u7406, which is actionable.' },
    { check_id: 'required_fields_present', description: 'All required fields present', passed: true, detail: 'Every required field is populated.' },
    { check_id: 'category_allowed', description: '\u533a\u5206 must be auto-confirmable', passed: true, detail: '\u7814\u4fee\u8cbb is in the policy list.' },
    { check_id: 'policy_reference_present', description: '\u53c2\u7167 must be present', passed: true, detail: 'Approval authority read from the detail panel.' },
    { check_id: 'amount_within_limit', description: '\u91d1\u984d within the configured prototype limit', passed: amountPassed, detail: amountDetail },
  ]
}

export const payrollJobs: AutomationJob[] = [
  {
    job_id: 'JOB-3001',
    workflow: 'PAYROLL_CONFIRMATION',
    state: 'COMPLETED',
    record: payrollItems.find((r) => r.record_id === 'DEMO-PAY-001')!,
    decision: {
      decision: 'APPROVE',
      reason:
        'Every gate passed: the item is unprocessed, \u7814\u4fee\u8cbb is auto-confirmable, the \u53c2\u7167 note is present, and the amount is within the configured prototype limit.',
      confidence: 0.95,
      human_review_required: false,
      ambiguity_type: null,
      policy_version: PAYROLL_POLICY,
      decided_at: minsAgo(6),
      decided_by: 'llm+policy_guard',
      policy_checks: payrollGates(true, '9800 JPY is at or below the prototype limit of 30000.'),
    },
    human_decision: null,
    execution: {
      action: 'CONFIRM_PAYROLL',
      workflow: 'PAYROLL_CONFIRMATION',
      record_id: 'DEMO-PAY-001',
      success: true,
      steps_completed: [
        { name: 'Open the work queue', completed: true, detail: '/mock-hr/payroll-items', error: null, at: minsAgo(6) },
        { name: 'Locate and open the record', completed: true, detail: 'Opened DEMO-PAY-001', error: null, at: minsAgo(6) },
        { name: 'Click \u767b\u9332\u78ba\u5b9a and submit', completed: true, detail: 'Located by [data-testid], not by position.', error: null, at: minsAgo(6) },
        { name: 'Independently re-read the record status', completed: true, detail: 'Re-read from the queue screen: status is \u767b\u9332\u78ba\u5b9a\u6e08\u307f.', error: null, at: minsAgo(6) },
      ],
      verification_status: 'VERIFIED',
      status_before: '\u672a\u51e6\u7406',
      status_after: '\u767b\u9332\u78ba\u5b9a\u6e08\u307f',
      error: null,
      started_at: minsAgo(6),
      finished_at: minsAgo(6),
      duration_seconds: 1.48,
      executed_by: 'agent',
    },
    state_history: [
      { from_state: 'START', to_state: 'LOADING', at: minsAgo(7), note: null },
      { from_state: 'POLICY_CHECK', to_state: 'EXECUTING', at: minsAgo(6), note: null },
      { from_state: 'VERIFYING', to_state: 'COMPLETED', at: minsAgo(6), note: 'Verified: \u672a\u51e6\u7406 -> \u767b\u9332\u78ba\u5b9a\u6e08\u307f' },
    ],
    error: null,
    created_at: minsAgo(7),
    updated_at: minsAgo(6),
  },
  {
    job_id: 'JOB-3002',
    workflow: 'PAYROLL_CONFIRMATION',
    state: 'HUMAN_REVIEW',
    record: payrollItems.find((r) => r.record_id === 'DEMO-PAY-REVIEW')!,
    decision: {
      decision: 'REVIEW',
      reason:
        'The amount exceeds the configured prototype limit. Dataset B never revealed the real approval thresholds, so anything above the configured value escalates rather than being refused.',
      confidence: 0.35,
      human_review_required: true,
      ambiguity_type: 'POLICY_NOT_COVERED',
      policy_version: PAYROLL_POLICY,
      decided_at: minsAgo(3),
      decided_by: 'llm+policy_guard',
      policy_checks: payrollGates(false, '148500 JPY exceeds the prototype limit of 30000.'),
    },
    human_decision: null,
    execution: null,
    state_history: [
      { from_state: 'ANALYZING', to_state: 'POLICY_CHECK', at: minsAgo(3), note: null },
      { from_state: 'POLICY_CHECK', to_state: 'HUMAN_REVIEW', at: minsAgo(3), note: 'Amount above the configured prototype limit.' },
    ],
    error: null,
    created_at: minsAgo(4),
    updated_at: minsAgo(3),
  },
]

/** Every job across both workflows - what `/api/automation/history` returns. */
export const allJobs: AutomationJob[] = [...payrollJobs, ...jobs]

/** Payroll rows nothing has run yet, plus the two that have. */
export const payrollQueueTasks: QueueTask[] = [
  ...payrollJobs.map((job, i): QueueTask => ({
    task_id: `#PR-${7700 + i}`,
    job_id: job.job_id,
    workflow: 'PAYROLL_CONFIRMATION',
    record: job.record,
    state: job.state,
    stage: STAGE_BY_STATE[job.state],
    decision: job.decision?.decision ?? null,
    confidence: job.decision?.confidence ?? null,
    submitted_at: job.created_at,
    detail_line: payrollDetailLine(job.record as PayrollItem),
    duration_label: job.execution ? `${job.execution.duration_seconds?.toFixed(2)}s` : '\u2014',
    duration_seconds: job.execution?.duration_seconds ?? null,
  })),
  ...payrollItems
    .filter((r) => !payrollJobs.some((j) => j.record.record_id === r.record_id))
    .map((r, i): QueueTask => ({
      task_id: `#PR-${7750 + i}`,
      job_id: '',
      workflow: 'PAYROLL_CONFIRMATION',
      record: r,
      state: 'START',
      stage: 'Queued',
      decision: null,
      confidence: null,
      submitted_at: minsAgo(40 + i * 5),
      detail_line: payrollDetailLine(r),
      duration_label: '\u2014',
      duration_seconds: null,
    })),
]

/** Mirrors the payroll branch of `detailLine` in services/api.ts. */
function payrollDetailLine(rec: PayrollItem): string {
  const gaps: string[] = []
  if (!rec.employee_id) gaps.push('employee_id missing')
  if (!rec.category) gaps.push('category missing')
  if (!rec.amount) gaps.push('amount missing')
  if (!rec.policy_reference) gaps.push('\u53c2\u7167 note missing')
  if (gaps.length) return gaps.join(' \u00b7 ')
  return [rec.category, `\u00a5${Number(rec.amount).toLocaleString('ja-JP')}`].join(' \u00b7 ')
}

/** Both queues, as the live `fetchQueue` assembles them. */
export const allQueueTasks: QueueTask[] = [...queueTasks, ...payrollQueueTasks]

/* ========================================================================== */
/* Prototype run metrics - mirrors GET /api/metrics                           */
/* ========================================================================== */

export const prototypeMetrics: PrototypeMetrics = {
  generated_at: minsAgo(1),
  sample: {
    total_runs: 26,
    execution_attempts: 10,
    note: 'Measured from runs this backend actually performed.',
  },
  automation_success: {
    verified: 10,
    attempted: 10,
    rate: 1.0,
    definition: 'successfully verified runs / runs that reached the browser.',
  },
  verification: {
    verified: 10,
    failed: 0,
    not_attempted: 0,
    rate: 1.0,
    definition: 'Did the record actually end up in the expected business state?',
  },
  automation_rate: {
    eligible_runs: 26,
    completed_without_human: 8,
    required_human_review: 18,
    still_awaiting_human: 16,
    failed: 0,
    automation_rate: 0.3077,
    review_rate: 0.6923,
    definition: 'Escalation is a designed outcome here, not a failure.',
  },
  execution_latency: {
    prototype_seconds: { n: 10, median: 1.32, mean: 1.392, fastest: 1.292, slowest: 1.685 },
    observed_human_baseline: {
      LEAVE_APPROVAL: {
        clean_instance_seconds: 4.365,
        family_median_seconds: 40.83,
        observed_executions: 23,
        observed_minutes: 18.63,
        segment: 'ses_20260701-180923-NEELA9BAF::seg013',
      },
      PAYROLL_CONFIRMATION: {
        clean_instance_seconds: 11.7,
        family_median_seconds: 28.82,
        observed_executions: 39,
        observed_minutes: 30.16,
        segment: 'ses_20260701-190250-NEELA9BAF::seg002',
      },
    },
    definition: 'Measured prototype execution latency. Never estimated.',
    caveat:
      'THIS IS NOT A SAVINGS FIGURE. Prototype latency is browser time against a local mock system; the Dataset B numbers are human time in a recorded test environment.',
  },
  safety: {
    policy_bypasses: 0,
    escalated_but_executed_without_authorisation: 0,
    guard_interventions: 0,
    model_wanted_to_act_but_was_stopped: 0,
    definition: 'A bypass is a run the policy engine wanted escalated that executed anyway.',
    observed_only_caveat:
      'Zero bypasses across a live sample proves little on its own - the adversarial probe is the real evidence.',
    adversarial_probe: {
      records_probed: 28,
      records_the_policy_wanted_escalated: 20,
      held_by_the_guard: 20,
      leaked: [],
      hold_rate: 1.0,
      definition: 'Every record re-evaluated with a maximally hostile model draft.',
    },
    claim_validated: 'The LLM cannot override deterministic safety controls.',
  },
  by_workflow: {
    LEAVE_APPROVAL: {
      runs: 16,
      execution_attempts: 5,
      verified: 5,
      success_rate: 1.0,
      autonomous: 4,
      automation_rate: 0.25,
      prototype_latency_seconds: { n: 5, median: 1.318, mean: 1.35, fastest: 1.292, slowest: 1.5 },
      observed_human_baseline: null,
    },
    PAYROLL_CONFIRMATION: {
      runs: 10,
      execution_attempts: 5,
      verified: 5,
      success_rate: 1.0,
      autonomous: 4,
      automation_rate: 0.4,
      prototype_latency_seconds: { n: 5, median: 1.322, mean: 1.43, fastest: 1.3, slowest: 1.685 },
      observed_human_baseline: null,
    },
  },
}
