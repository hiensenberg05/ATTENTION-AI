/**
 * API service layer — now live against the FastAPI backend.
 *
 * Every screen talks to this module, never to `fetch` or to mock data directly,
 * which is why switching the whole console from fabricated data to real agent
 * runs was a change in this one file.
 *
 * Endpoints consumed:
 *   GET  /api/workflows                            workflow definitions + Phase 2 evidence
 *   GET  /api/leave-requests                       the leave queue, live
 *   GET  /api/leave-requests/{record_id}
 *   GET  /api/payroll-items                        the payroll queue, live
 *   GET  /api/payroll-items/{record_id}
 *   GET  /api/policy/leave  |  /api/policy/payroll the explicit prototype policies
 *   POST /api/automation/{workflow}/{record_id}/start   run one record, either workflow
 *   GET  /api/automation/history                   every job this backend has run
 *   GET  /api/automation/{job_id}
 *   POST /api/automation/{job_id}/human-decision   resolve an escalated job
 *   POST /api/demo/reset                           restore the HR system + clear jobs
 *
 * WHAT IS DERIVED HERE, AND WHY: the backend deliberately exposes jobs rather
 * than pre-chewed view models, so screen-shaped things — queue stages, run-history
 * rows, dashboard counters — are computed in this module from real jobs. Nothing
 * below invents a number: if no job has run, the counters are zero and the screens
 * say so, rather than showing a plausible-looking figure.
 */

import type {
  AutomationJob,
  BusinessRecord,
  DecisionType,
  ExecutionResult,
  JobState,
  LeaveRequest,
  PayrollItem,
  QueueStage,
  QueueTask,
  RunHistoryEntry,
  WorkflowDefinition,
  WorkflowType,
} from '@/types'
import { isLeaveRequest } from '@/types'

const API_BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — GET ${path}`)
  return (await res.json()) as T
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const payload = (await res.json()) as { detail?: unknown }
      if (payload.detail) detail = typeof payload.detail === 'string' ? payload.detail : detail
    } catch {
      /* non-JSON error body — keep the status line */
    }
    throw new Error(`${detail} — POST ${path}`)
  }
  return (await res.json()) as T
}

/* ---- reference data ------------------------------------------------------ */

export async function fetchWorkflows(): Promise<WorkflowDefinition[]> {
  return get<WorkflowDefinition[]>('/workflows')
}

export async function fetchWorkflow(w: WorkflowType): Promise<WorkflowDefinition | null> {
  return get<WorkflowDefinition>(`/workflows/${w}`)
}

export async function fetchLeaveRequests(status?: string): Promise<LeaveRequest[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : ''
  return get<LeaveRequest[]>(`/leave-requests${qs}`)
}

export async function fetchLeaveRequest(recordId: string): Promise<LeaveRequest> {
  return get<LeaveRequest>(`/leave-requests/${encodeURIComponent(recordId)}`)
}

export async function fetchPayrollItems(status?: string): Promise<PayrollItem[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : ''
  return get<PayrollItem[]>(`/payroll-items${qs}`)
}

export async function fetchPayrollItem(recordId: string): Promise<PayrollItem> {
  return get<PayrollItem>(`/payroll-items/${encodeURIComponent(recordId)}`)
}

export async function fetchAgentHealth(): Promise<{
  llm_configured: boolean
  model: string
  provider: string
  api_key_present: boolean
  pydantic_ai_version: string | null
  fallback: string
}> {
  return get('/agent/health')
}

/* ---- jobs ---------------------------------------------------------------- */

export async function fetchJobs(): Promise<AutomationJob[]> {
  return get<AutomationJob[]>('/automation/history')
}

export async function fetchJob(jobId: string): Promise<AutomationJob> {
  return get<AutomationJob>(`/automation/${encodeURIComponent(jobId)}`)
}

/**
 * Run one record through the pipeline: policy evaluation, LLM decision, Python
 * guards, and — unless the job escalates — Playwright execution and verification.
 * Resolves when the run is finished, so callers get a real outcome rather than a
 * job id to poll.
 *
 * One endpoint serves every workflow, because it is the same pipeline.
 */
export async function startAutomation(
  workflow: WorkflowType,
  recordId: string,
): Promise<AutomationJob> {
  return post<AutomationJob>(
    `/automation/${workflow}/${encodeURIComponent(recordId)}/start`,
  )
}

export async function startLeaveAutomation(recordId: string): Promise<AutomationJob> {
  return startAutomation('LEAVE_APPROVAL', recordId)
}

export async function submitHumanDecision(
  jobId: string,
  decision: 'APPROVE' | 'REJECT',
  note: string,
  operator = 'operator',
): Promise<AutomationJob> {
  return post<AutomationJob>(`/automation/${encodeURIComponent(jobId)}/human-decision`, {
    decision,
    operator,
    note,
  })
}

export async function resetDemo(): Promise<{ status: string; records_restored: number }> {
  return post('/demo/reset')
}

/* ---- derived view models ------------------------------------------------- */

const STAGE_BY_STATE: Record<JobState, QueueStage> = {
  START: 'Queued',
  LOADING: 'Agent Evaluating',
  VALIDATING: 'Agent Evaluating',
  ANALYZING: 'Agent Evaluating',
  POLICY_CHECK: 'Agent Evaluating',
  HUMAN_REVIEW: 'Pending Human Sign-off',
  EXECUTING: 'Executing',
  VERIFYING: 'Verifying',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
}

function recordOf(job: AutomationJob): BusinessRecord {
  return job.record
}

/** Money as the HR screen prints it: grouped, with the unit. */
function yen(amount: string | null): string {
  if (!amount) return ''
  const n = Number(amount)
  return Number.isFinite(n) ? `¥${n.toLocaleString('ja-JP')}` : amount
}

/**
 * The one-line summary under a queue row. Missing fields are named rather than
 * rendered blank, because a gap in the record is the thing most likely to send
 * it to a human.
 */
function detailLine(rec: BusinessRecord): string {
  const gaps: string[] = []
  if (!rec.employee_id) gaps.push('employee_id missing')

  if (isLeaveRequest(rec)) {
    if (!rec.request_date) gaps.push('date missing')
    if (!rec.department) gaps.push('department missing')
    if (gaps.length) return gaps.join(' · ')
    return [rec.request_type, rec.request_date, rec.department].filter(Boolean).join(' · ')
  }

  if (!rec.category) gaps.push('category missing')
  if (!rec.amount) gaps.push('amount missing')
  if (!rec.policy_reference) gaps.push('参照 note missing')
  if (gaps.length) return gaps.join(' · ')
  return [rec.category, yen(rec.amount)].filter(Boolean).join(' · ')
}

function durationLabel(job: AutomationJob | null): string {
  if (!job?.execution?.duration_seconds) return '—'
  return `${job.execution.duration_seconds.toFixed(2)}s`
}

/**
 * The work queue: every leave record, annotated with the most recent job run
 * against it. Records nobody has run yet are 'Queued' with no decision — which is
 * the honest state, not an omission.
 */
export async function fetchQueue(): Promise<QueueTask[]> {
  const [leave, payroll, jobs] = await Promise.all([
    fetchLeaveRequests(),
    fetchPayrollItems(),
    fetchJobs(),
  ])

  // Jobs arrive newest-first, so the first match per record is the latest run.
  // Keyed by workflow AND id, because the two queues use different id schemes and
  // a future collision must not make one workflow's job annotate the other's row.
  const latest = new Map<string, AutomationJob>()
  for (const job of jobs) {
    const key = `${job.workflow}:${recordOf(job).record_id}`
    if (!latest.has(key)) latest.set(key, job)
  }

  const rows: Array<{ workflow: WorkflowType; record: BusinessRecord }> = [
    ...leave.map((record) => ({ workflow: 'LEAVE_APPROVAL' as const, record })),
    ...payroll.map((record) => ({ workflow: 'PAYROLL_CONFIRMATION' as const, record })),
  ]

  return rows.map(({ workflow, record }, i) => {
    const job = latest.get(`${workflow}:${record.record_id}`) ?? null
    return {
      task_id: `TASK-${String(i + 1).padStart(3, '0')}`,
      job_id: job?.job_id ?? '',
      workflow,
      record,
      state: job?.state ?? 'START',
      stage: job ? STAGE_BY_STATE[job.state] : 'Queued',
      decision: job?.decision?.decision ?? null,
      confidence: job?.decision?.confidence ?? null,
      submitted_at: job?.created_at ?? new Date().toISOString(),
      detail_line: detailLine(record),
      duration_label: durationLabel(job),
      duration_seconds: job?.execution?.duration_seconds ?? null,
    }
  })
}

/** Run history: one row per job that actually reached the browser. */
export async function fetchRunHistory(): Promise<RunHistoryEntry[]> {
  const jobs = await fetchJobs()
  return jobs
    .filter((j): j is AutomationJob & { execution: ExecutionResult } => j.execution !== null)
    .map((job) => {
      const rec = recordOf(job)
      const effective: DecisionType =
        job.human_decision?.decision ?? job.decision?.decision ?? 'REVIEW'
      const leave = isLeaveRequest(rec)
      return {
        run_id: job.job_id.replace('JOB-', 'RUN-'),
        job_id: job.job_id,
        timestamp: job.execution.finished_at ?? job.updated_at,
        workflow: job.workflow,
        subject: rec.employee_name ?? rec.record_id,
        subject_detail: leave
          ? [rec.request_type, rec.request_date].filter(Boolean).join(' · ')
          : [rec.category, yen(rec.amount)].filter(Boolean).join(' · '),
        decision: effective,
        human_overridden: job.human_decision !== null,
        verification_status: job.execution.verification_status,
        duration_ms: Math.round((job.execution.duration_seconds ?? 0) * 1000),
        systems_touched: [
          leave ? 'Mock HR (leave-applications)' : 'Mock HR (payroll-items)',
        ],
      }
    })
}

/**
 * Dashboard counters, computed from real runs only.
 *
 * The shape matches what the screens already consume, so connecting the backend
 * changed this module and nothing else. What changed is where the numbers come
 * from: every one of them is now derived from jobs this backend actually ran. If
 * nothing has run, they are zero — the console shows an empty system rather than
 * a plausible-looking one.
 *
 * `autonomousRate` is deliberately "finished without a human / all finished jobs".
 * A job a person had to resolve is not automation, even when it then succeeded.
 */
export async function fetchDashboard() {
  const [jobs, leave, payroll] = await Promise.all([
    fetchJobs(),
    fetchLeaveRequests(),
    fetchPayrollItems(),
  ])
  const records: BusinessRecord[] = [...leave, ...payroll]

  const completed = jobs.filter((j) => j.state === 'COMPLETED')
  const failed = jobs.filter((j) => j.state === 'FAILED')
  const humanReview = jobs.filter((j) => j.state === 'HUMAN_REVIEW')
  const inFlight = jobs.filter(
    (j) => !['COMPLETED', 'FAILED', 'HUMAN_REVIEW'].includes(j.state),
  )
  const finished = [...completed, ...failed]
  const autonomous = completed.filter((j) => j.human_decision === null)

  const attempted = jobs.filter(
    (j) => j.execution && j.execution.verification_status !== 'NOT_ATTEMPTED',
  )
  const verified = jobs.filter((j) => j.execution?.verification_status === 'VERIFIED')

  const durations = jobs
    .map((j) => j.execution?.duration_seconds)
    .filter((d): d is number => typeof d === 'number' && d > 0)

  const ranRecordIds = new Set(jobs.map((j) => `${j.workflow}:${recordOf(j).record_id}`))
  const keyOf = (r: BusinessRecord) =>
    `${isLeaveRequest(r) ? 'LEAVE_APPROVAL' : 'PAYROLL_CONFIRMATION'}:${r.record_id}`

  const decided = jobs.filter((j) => j.decision)
  const decisions = {
    approve: decided.filter((j) => j.decision!.decision === 'APPROVE').length,
    review: decided.filter((j) => j.decision!.decision === 'REVIEW').length,
    reject: decided.filter((j) => j.decision!.decision === 'REJECT').length,
    total: decided.length,
  }

  // Real runs bucketed by calendar day. A single demo session is a single bar,
  // which is the honest picture rather than a manufactured 30-day trend.
  const byDay = new Map<string, { auto: number; human: number }>()
  for (const job of finished) {
    const day = (job.execution?.finished_at ?? job.updated_at).slice(0, 10)
    const bucket = byDay.get(day) ?? { auto: 0, human: 0 }
    if (job.human_decision) bucket.human += 1
    else bucket.auto += 1
    byDay.set(day, bucket)
  }
  const throughput = [...byDay.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, v], i) => ({ day: i, auto: v.auto, human: v.human }))

  return {
    metrics: {
      totalJobs: jobs.length,
      completed: completed.length,
      failed: failed.length,
      humanReview: humanReview.length,
      inFlight: inFlight.length,
      // Records nobody has run yet.
      queued: records.filter((r) => !ranRecordIds.has(keyOf(r))).length,
      autonomousRate: finished.length ? autonomous.length / finished.length : 0,
      verificationRate: attempted.length ? verified.length / attempted.length : 0,
      avgExecutionSeconds: durations.length
        ? durations.reduce((a, b) => a + b, 0) / durations.length
        : 0,
      // "Pending" means actionable in whichever queue the record belongs to.
      pendingRecords: records.filter(
        (r) => r.status === '申請中' || r.status === '未処理',
      ).length,
      llmDecisions: jobs.filter((j) => j.decision?.decided_by === 'llm+policy_guard').length,
    },
    decisions,
    connectors: [
      {
        name: 'Mock HR · 休暇申請',
        detail: 'Target UI · /mock-hr/leave-applications',
        status: 'connected' as const,
      },
      {
        name: 'Mock HR · 経費精算',
        detail: 'Target UI · /mock-hr/payroll-items',
        status: 'connected' as const,
      },
      {
        name: 'FastAPI backend',
        detail: 'localhost:8000 · agent + executor live',
        status: 'connected' as const,
      },
      {
        name: 'Groq · openai/gpt-oss-20b',
        detail: 'Policy decision drafting via PydanticAI',
        status: 'connected' as const,
      },
      {
        name: 'Playwright executor',
        detail: 'Chromium · deterministic browser actions',
        status: 'connected' as const,
      },
    ],
    throughput,
  }
}

export type DashboardData = Awaited<ReturnType<typeof fetchDashboard>>
