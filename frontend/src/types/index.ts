/**
 * TypeScript mirrors of the backend Pydantic schemas (`backend/models/`).
 *
 * Kept deliberately 1:1 with the Python models so that swapping the mock service
 * for live FastAPI calls is a data-source change, not a refactor. If a backend
 * model changes, change it here in the same commit.
 */

/* ---- backend/models/common.py ------------------------------------------- */

export type Provenance =
  | 'dataset_b_observed'
  | 'dataset_b_list_observed'
  | 'synthetic_demo'

export type WorkflowType = 'LEAVE_APPROVAL' | 'PAYROLL_CONFIRMATION'

export type DecisionType = 'APPROVE' | 'REJECT' | 'REVIEW'

export type AmbiguityType =
  | 'MISSING_REQUIRED_DATA'
  | 'POLICY_NOT_COVERED'
  | 'LOW_CONFIDENCE'
  | 'CONFLICTING_SIGNALS'
  | 'ACTION_NOT_AUTO_EXECUTABLE'

export type LeaveStatus = '申請中' | '承認済み' | '差戻し'
export type PayrollStatus = '未処理' | '登録確定済み' | '保留'

/* ---- backend/state/machine.py ------------------------------------------- */

export type JobState =
  | 'START'
  | 'LOADING'
  | 'VALIDATING'
  | 'ANALYZING'
  | 'POLICY_CHECK'
  | 'HUMAN_REVIEW'
  | 'EXECUTING'
  | 'VERIFYING'
  | 'COMPLETED'
  | 'FAILED'

/** Pipeline order for progress rendering. Terminal states sit outside it. */
export const JOB_STATE_SEQUENCE: JobState[] = [
  'START',
  'LOADING',
  'VALIDATING',
  'ANALYZING',
  'POLICY_CHECK',
  'EXECUTING',
  'VERIFYING',
  'COMPLETED',
]

/* ---- backend/models/leave.py -------------------------------------------- */

export interface LeaveRequest {
  record_id: string
  status: LeaveStatus
  employee_id: string | null
  employee_name: string | null
  request_type: string | null
  request_date: string | null
  department: string | null
  /** 事前承認要否 — null means UNKNOWN (detail panel never opened), not false. */
  prior_approval_required: boolean | null
  /** Prototype-only field. Dataset B never showed whether approval was obtained. */
  prior_approval_obtained: boolean | null
  comment: string | null
  provenance: Provenance
  evidence_note: string | null
}

/* ---- backend/models/payroll.py ------------------------------------------ */

export interface PayrollItem {
  record_id: string
  status: PayrollStatus
  employee_id: string | null
  employee_name: string | null
  category: string | null
  amount: string | null
  policy_reference: string | null
  comment: string | null
  provenance: Provenance
  evidence_note: string | null
}

export type BusinessRecord = LeaveRequest | PayrollItem

export function isLeaveRequest(r: BusinessRecord): r is LeaveRequest {
  return 'request_type' in r
}

/* ---- backend/models/agent.py -------------------------------------------- */

export interface PolicyCheck {
  check_id: string
  description: string
  /** true = passed, false = failed, null = could not be evaluated. */
  passed: boolean | null
  detail: string | null
  /** UI-only: which system the evidence for this check came from. */
  source?: string
}

export interface AgentDecision {
  decision: DecisionType
  reason: string
  confidence: number
  policy_checks: PolicyCheck[]
  human_review_required: boolean
  ambiguity_type: AmbiguityType | null
  policy_version: string | null
  decided_at: string | null
  /** 'llm+policy_guard' when the Groq-backed agent drafted it, or
   *  'policy_engine_fallback' when the model was unavailable and the
   *  deterministic rules decided alone. */
  decided_by: string | null
}

/* ---- backend/models/execution.py ---------------------------------------- */

export type ExecutionAction =
  | 'APPROVE_LEAVE'
  | 'REJECT_LEAVE'
  | 'CONFIRM_PAYROLL'
  | 'HOLD_PAYROLL'

export type VerificationStatus =
  | 'NOT_ATTEMPTED'
  | 'VERIFIED'
  | 'FAILED'
  | 'NOT_APPLICABLE'

export interface ExecutionStep {
  name: string
  completed: boolean
  detail: string | null
  error: string | null
  at: string | null
}

export interface ExecutionResult {
  action: ExecutionAction
  workflow: WorkflowType
  record_id: string
  success: boolean
  steps_completed: ExecutionStep[]
  verification_status: VerificationStatus
  status_before: string | null
  status_after: string | null
  error: string | null
  started_at: string | null
  finished_at: string | null
  duration_seconds: number | null
  executed_by: string | null
}

/* ---- backend/models/job.py ---------------------------------------------- */

export interface StateTransition {
  from_state: JobState
  to_state: JobState
  at: string
  note: string | null
}

/** An operator's determination on a record the agent escalated.
 *  Held alongside `decision`, never replacing it. */
export interface HumanDecision {
  decision: DecisionType
  operator: string
  note: string
  at: string
}

export interface AutomationJob {
  job_id: string
  workflow: WorkflowType
  state: JobState
  record: BusinessRecord
  decision: AgentDecision | null
  human_decision: HumanDecision | null
  execution: ExecutionResult | null
  state_history: StateTransition[]
  error: string | null
  created_at: string
  updated_at: string
}

/* ---- backend/workflows/base.py ------------------------------------------ */

export interface WorkflowStepSpec {
  step_id: string
  name: string
  description: string
  state: JobState
  automated: boolean
}

export interface ExecutionActionSpec {
  decision: DecisionType
  action: ExecutionAction
  ui_target_label: string
  auto_executable: boolean
  rationale: string
}

export interface WorkflowEvidence {
  dataset: string
  process_type_id: string
  observed_executions: number
  observed_minutes: number
  observed_workers: number
  observed_sessions: number
  family_median_duration_seconds: number
  clean_instance_segment_id: string
  clean_instance_duration_seconds: number
  clean_instance_event_count: number
  phase2_confidence_level: string
  visually_confirmed: boolean
  source_documents: string[]
  caveats: string[]
}

export interface WorkflowDefinition {
  workflow: WorkflowType
  name: string
  description: string
  implemented: boolean
  record_model: string
  policy_key: string
  steps: WorkflowStepSpec[]
  supported_decisions: DecisionType[]
  execution_actions: ExecutionActionSpec[]
  verification: {
    method: string
    status_before: string
    expected_status_after: Record<string, string>
    expected_status_observed_in_dataset_b: boolean
    note: string | null
  }
  evidence: WorkflowEvidence
}

/* ---- UI-only view models ------------------------------------------------ */

/** Queue stage shown in the task list — derived from job state, not a new axis. */
export type QueueStage =
  | 'Queued'
  | 'Agent Evaluating'
  | 'Pending Human Sign-off'
  | 'Executing'
  | 'Verifying'
  | 'Completed'
  | 'Failed'

export interface QueueTask {
  task_id: string
  job_id: string
  workflow: WorkflowType
  record: BusinessRecord
  state: JobState
  stage: QueueStage
  decision: DecisionType | null
  confidence: number | null
  /** When the JOB was created. Null when nothing has run this record - the mock
   *  HR system carries no submission timestamp, so inventing one would be a lie. */
  submitted_at: string | null
  detail_line: string
  duration_label: string
  /** Measured execution time, or null if this record has not been executed. */
  duration_seconds: number | null
}

export interface RunHistoryEntry {
  run_id: string
  job_id: string
  timestamp: string
  workflow: WorkflowType
  subject: string
  subject_detail: string
  decision: DecisionType
  human_overridden: boolean
  verification_status: VerificationStatus
  duration_ms: number
  systems_touched: string[]
}
