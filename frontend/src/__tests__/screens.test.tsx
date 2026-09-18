/**
 * Render smoke tests for every screen.
 *
 * These mount each route in jsdom, wait for the (mock) API to resolve, and
 * assert the populated state actually appears — not just that the component
 * imported. They catch the class of bug a typecheck cannot: bad property
 * access, undefined maps, crashes on mount, broken navigation wiring.
 *
 * Page-content assertions are scoped to <main> because several sidebar nav
 * labels legitimately duplicate page titles.
 */

import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import Dashboard from '@/pages/Dashboard'
import TaskQueue from '@/pages/TaskQueue'
import AgentProcessing from '@/pages/AgentProcessing'
import Execution from '@/pages/Execution'
import HumanReview from '@/pages/HumanReview'
import AuditHistory from '@/pages/AuditHistory'
import {
  allJobs,
  allQueueTasks,
  computeMetrics,
  decisionDistribution,
  leaveRequests,
  payrollItems,
  payrollJobs,
  prototypeMetrics,
  runHistory,
  systemConnectors,
  throughputSeries,
  workflows,
} from './fixtures'

/**
 * `services/api` talks to the real backend, so these tests replace it with the
 * fixtures in `./fixtures.ts`. That keeps what these tests are actually for -
 * proving every screen renders its populated state without crashing - while
 * leaving the backend contract to the Python side, where it can be checked
 * against a real server rather than a stub.
 */
vi.mock('@/services/api', () => ({
  fetchWorkflows: async () => workflows,
  fetchWorkflow: async (w: string) => workflows.find((x) => x.workflow === w) ?? null,
  fetchLeaveRequests: async (status?: string) =>
    status ? leaveRequests.filter((r) => r.status === status) : leaveRequests,
  fetchLeaveRequest: async (id: string) => {
    const found = leaveRequests.find((r) => r.record_id === id)
    if (!found) throw new Error(`No leave request ${id}`)
    return found
  },
  fetchPayrollItems: async (status?: string) =>
    status ? payrollItems.filter((r) => r.status === status) : payrollItems,
  fetchPayrollItem: async (id: string) => {
    const found = payrollItems.find((r) => r.record_id === id)
    if (!found) throw new Error(`No payroll item ${id}`)
    return found
  },
  fetchQueue: async () => allQueueTasks,
  fetchJobs: async () => allJobs,
  fetchJob: async (id: string) => {
    const found = allJobs.find((j) => j.job_id === id)
    if (!found) throw new Error(`No job ${id}`)
    return found
  },
  fetchRunHistory: async () => runHistory,
  fetchPrototypeMetrics: async () => prototypeMetrics,
  fetchDashboard: async () => ({
    metrics: computeMetrics(),
    decisions: decisionDistribution(),
    connectors: systemConnectors,
    throughput: throughputSeries,
  }),
  fetchAgentHealth: async () => ({
    llm_configured: true,
    model: 'openai/gpt-oss-20b',
    provider: 'groq',
    api_key_present: true,
    pydantic_ai_version: '2.44.0',
    fallback: 'deterministic policy engine',
  }),
  startAutomation: async (_workflow: string, recordId: string) =>
    allJobs.find((j) => (j.record as { record_id: string }).record_id === recordId) ?? allJobs[0],
  startLeaveAutomation: async (recordId: string) =>
    allJobs.find((j) => (j.record as { record_id: string }).record_id === recordId) ?? allJobs[0],
  submitHumanDecision: async (jobId: string) =>
    allJobs.find((j) => j.job_id === jobId) ?? allJobs[0],
  resetDemo: async () => ({ status: 'reset', records_restored: leaveRequests.length }),
}))

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppShell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/queue" element={<TaskQueue />} />
          <Route path="/agent" element={<AgentProcessing />} />
          <Route path="/agent/:jobId" element={<AgentProcessing />} />
          <Route path="/execution" element={<Execution />} />
          <Route path="/execution/:jobId" element={<Execution />} />
          <Route path="/review" element={<HumanReview />} />
          <Route path="/review/:jobId" element={<HumanReview />} />
          <Route path="/history" element={<AuditHistory />} />
        </Routes>
      </AppShell>
    </MemoryRouter>,
  )
}

const settle = { timeout: 4000 }

/** Scope queries to the page content area. */
const page = () => within(screen.getByRole('main'))

describe('app shell', () => {
  it('renders navigation to every major screen', () => {
    renderAt('/')
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    for (const label of [
      'Overview & Metrics',
      'Workflow Task Queue',
      'Agent Policy & Decision',
      'Step Automation Execution',
      'Human Review Queue',
      'Audit & Run History',
    ]) {
      expect(within(nav).getByText(label)).toBeTruthy()
    }
  })
})

describe('dashboard', () => {
  it('renders KPIs, workflow evidence and the decision stream', async () => {
    renderAt('/')
    await waitFor(() => expect(page().getByText('Operations Overview')).toBeTruthy(), settle)
    await waitFor(() => expect(page().getByText('Automated workflows')).toBeTruthy(), settle)

    // Real Phase 2 evidence numbers must be on screen, not invented ones.
    expect(page().getByText('23')).toBeTruthy() // leave observed executions
    expect(page().getByText('18.63')).toBeTruthy() // leave observed minutes
    expect(page().getByText('39')).toBeTruthy() // payroll observed executions

    // The honesty notice travels with the counters, naming what is still a stand-in.
    expect(page().getByText(/Prototype environment\./)).toBeTruthy()

    // Pipeline strip renders all six deterministic stages.
    for (const stage of ['Load', 'Validate', 'Analyze', 'Policy check', 'Execute', 'Verify']) {
      expect(page().getAllByText(stage).length).toBeGreaterThan(0)
    }
  })

  it('numbers each implemented workflow distinctly', async () => {
    renderAt('/')
    await waitFor(() => expect(page().getByText('Automated workflows')).toBeTruthy(), settle)

    // Both workflows shipped, so both carry a badge - and they must not both
    // claim to be the first one. The badge used to be the literal 'Workflow #1'
    // for every implemented workflow, which made payroll look like leave.
    expect(page().getByText('Workflow #1')).toBeTruthy()
    expect(page().getByText('Workflow #2')).toBeTruthy()
    expect(page().queryAllByText('Workflow #1').length).toBe(1)
  })
})

describe('task queue', () => {
  it('renders every queued task with provenance', async () => {
    renderAt('/queue')
    await waitFor(() => expect(page().getByText(/Showing/)).toBeTruthy(), settle)

    // The Dataset B grounded record must be visible and labelled as observed.
    expect(page().getAllByText('P2-07048822-006').length).toBeGreaterThan(0)
    expect(page().getAllByText('Observed in Dataset B').length).toBeGreaterThan(0)
    expect(page().getAllByText('Synthetic demo record').length).toBeGreaterThan(0)

    // Missing-data records surface their gaps rather than rendering blank.
    expect(page().getAllByText('employee_id missing').length).toBeGreaterThan(0)
    expect(page().getAllByText('date missing').length).toBeGreaterThan(0)
  })

  it('shows one row per task', async () => {
    renderAt('/queue')
    await waitFor(() => expect(page().getByText(/Showing/)).toBeTruthy(), settle)
    // header row + one row per task
    expect(page().getAllByRole('row').length).toBe(allQueueTasks.length + 1)
  })

  it('offers a live workflow filter and a CSV export of what is on screen', async () => {
    renderAt('/queue')
    await waitFor(() => expect(page().getByText(/Showing/)).toBeTruthy(), settle)

    // Both controls used to be decorative - no handler, nothing behind them.
    // The export names its own row count, so a dead button is visible as one.
    expect(page().getByText(`Export CSV (${allQueueTasks.length})`)).toBeTruthy()

    const filter = page().getByLabelText('Filter by workflow') as HTMLSelectElement
    expect(filter.value).toBe('all')
    expect([...filter.options].map((o) => o.value)).toEqual(['all', 'leave', 'payroll'])
  })

  it('names both workflows in the header rather than only the first', async () => {
    renderAt('/queue')
    await waitFor(() => expect(page().getByText(/Showing/)).toBeTruthy(), settle)
    // Was the literal "Leave Approval active", which payroll shipping made false.
    expect(page().getByText('2 workflows active')).toBeTruthy()
  })
})

describe('agent processing', () => {
  it('renders the policy gates and decision for an approved job', async () => {
    renderAt('/agent/JOB-2042')
    await waitFor(() => expect(page().getByText(/Policy evaluation:/)).toBeTruthy(), settle)

    expect(page().getByText('Policy engine verification')).toBeTruthy()
    expect(page().getAllByText(/Gate 1\./).length).toBeGreaterThan(0)
    expect(page().getAllByText('PASS').length).toBe(4)
    expect(page().getByText(/Recommended for auto-approval/)).toBeTruthy()
    // The policy-provenance disclaimer must be shown with the gates.
    expect(page().getByText(/Nothing here was learned from the/)).toBeTruthy()
  })

  it('marks a non-evaluable gate rather than treating it as a failure', async () => {
    renderAt('/agent/JOB-2041')
    await waitFor(() => expect(page().getByText(/Policy evaluation:/)).toBeTruthy(), settle)
    expect(page().getByText('NOT EVALUABLE')).toBeTruthy()
    expect(page().getByText(/Escalated to human review/)).toBeTruthy()
  })

  it('lists decided jobs when no job is selected', async () => {
    renderAt('/agent')
    await waitFor(() => expect(page().getByText('Agent Policy & Decision')).toBeTruthy(), settle)
    await waitFor(() => expect(page().getAllByText(/JOB-20/).length).toBeGreaterThan(0), settle)
  })
})

describe('execution', () => {
  it('renders deterministic steps and the verification transition', async () => {
    renderAt('/execution/JOB-2039')
    await waitFor(() => expect(page().getByText(/Execution:/)).toBeTruthy(), settle)

    expect(page().getByText('Deterministic steps')).toBeTruthy()
    expect(page().getAllByText(/Click 承認/).length).toBeGreaterThan(0)
    expect(page().getByText('Verification')).toBeTruthy()
    // before -> after status transition is shown
    expect(page().getAllByText('申請中').length).toBeGreaterThan(0)
    expect(page().getAllByText('承認済み').length).toBeGreaterThan(0)
    // the prototype-assumption caveat travels with the verification claim
    expect(page().getByText(/prototype assumption/i)).toBeTruthy()
  })

  it('shows a failed verification distinctly from a failed click', async () => {
    renderAt('/execution/JOB-2038')
    await waitFor(() => expect(page().getByText(/Execution:/)).toBeTruthy(), settle)
    expect(page().getByText('Verification failed')).toBeTruthy()
  })
})

describe('human review', () => {
  it('renders the escalation queue', async () => {
    renderAt('/review')
    await waitFor(() => expect(page().getByText('Human Review Queue')).toBeTruthy(), settle)
    // Both workflows escalate into the same queue, so the count spans both.
    const reviewCount = allJobs.filter((j) => j.state === 'HUMAN_REVIEW').length
    await waitFor(
      () => expect(page().getByText(`${reviewCount} awaiting`)).toBeTruthy(),
      settle,
    )
  })

  it('renders the operator determination form for one job', async () => {
    renderAt('/review/JOB-2041')
    await waitFor(() => expect(page().getByText(/^Review:/)).toBeTruthy(), settle)

    expect(page().getByText('Operator determination')).toBeTruthy()
    expect(page().getByText('Approve with justification')).toBeTruthy()
    expect(page().getByText('Reject request')).toBeTruthy()
    expect(page().getByLabelText('Audit note')).toBeTruthy()

    // Confirm is gated until a determination AND an audit note exist.
    const confirm = page().getByRole('button', { name: /Confirm decision/ })
    expect((confirm as HTMLButtonElement).disabled).toBe(true)

    // The never-auto-reject rule must be stated on this screen.
    expect(page().getByText(/Reject is never automatic\./)).toBeTruthy()
  })

  it('explains the unknown prior-approval field honestly', async () => {
    renderAt('/review/JOB-2041')
    await waitFor(() => expect(page().getByText(/^Review:/)).toBeTruthy(), settle)
    expect(page().getAllByText(/never whether it was/).length).toBeGreaterThan(0)
    expect(page().getAllByText(/obtained: Unknown/).length).toBeGreaterThan(0)
  })
})

describe('audit history', () => {
  it('renders run rows, charts and the evidence-vs-runs distinction', async () => {
    renderAt('/history')
    await waitFor(() => expect(page().getByText(/Showing/)).toBeTruthy(), settle)

    expect(page().getByText('Breakdown by workflow')).toBeTruthy()
    expect(page().getAllByText(/RUN-/).length).toBeGreaterThan(0)
    expect(page().getByText(/What this audit trail is, and is not/)).toBeTruthy()
  })
})

describe('payroll confirmation', () => {
  it('shows payroll records alongside leave in one queue', async () => {
    renderAt('/queue')
    await waitFor(() => expect(page().getByText(/Showing/)).toBeTruthy(), settle)

    // Both workflows are present and labelled, so two queues in one table are
    // never ambiguous.
    expect(page().getAllByText('Payroll Confirmation').length).toBeGreaterThan(0)
    expect(page().getAllByText('Leave Approval').length).toBeGreaterThan(0)

    // The screenshot-confirmed payroll record, with its real amount.
    expect(page().getAllByText('P1-07046967-001').length).toBeGreaterThan(0)
    expect(page().getAllByText(/¥25,213/).length).toBeGreaterThan(0)
  })

  it('renders the payroll policy gates and a confirmed execution', async () => {
    renderAt('/agent/JOB-3001')
    await waitFor(() => expect(page().getByText(/Policy evaluation:/)).toBeTruthy(), settle)
    expect(page().getAllByText('PASS').length).toBe(5)
    expect(page().getAllByText(/金額/).length).toBeGreaterThan(0)
  })

  it('escalates an amount above the configured prototype limit', async () => {
    renderAt('/agent/JOB-3002')
    await waitFor(() => expect(page().getByText(/Policy evaluation:/)).toBeTruthy(), settle)
    expect(page().getByText('FAIL')).toBeTruthy()
    expect(page().getByText(/Escalated to human review/)).toBeTruthy()
    // The threshold must never be presented as a company rule.
    expect(page().getAllByText(/prototype limit/).length).toBeGreaterThan(0)
  })

  it('shows the payroll execution with its verified status change', async () => {
    renderAt('/execution/JOB-3001')
    await waitFor(() => expect(page().getByText(/Execution:/)).toBeTruthy(), settle)
    expect(page().getAllByText(/Click 登録確定/).length).toBeGreaterThan(0)
    expect(page().getAllByText('未処理').length).toBeGreaterThan(0)
    expect(page().getAllByText('登録確定済み').length).toBeGreaterThan(0)
  })

  it('mirrors the backend payroll dataset, provenance intact', () => {
    const observed = payrollItems.find((r) => r.record_id === 'P1-07046967-001')!
    expect(observed.provenance).toBe('dataset_b_observed')
    expect(observed.amount).toBe('25213')
    expect(observed.category).toBe('研修費')
    // Synthetic payroll records must wear an unmistakable prefix.
    for (const rec of payrollItems) {
      if (rec.provenance === 'synthetic_demo') {
        expect(rec.record_id.startsWith('DEMO-')).toBe(true)
      }
    }
  })

  it('never auto-executes a hold', () => {
    for (const job of payrollJobs) {
      if (job.decision?.decision === 'REVIEW') expect(job.execution).toBeNull()
    }
  })
})

describe('no hardcoded figures', () => {
  it('states record counts from data, not from a literal', async () => {
    renderAt('/')
    await waitFor(() => expect(page().getByText('Operations Overview')).toBeTruthy(), settle)

    const total = leaveRequests.length + payrollItems.length
    const observed = [...leaveRequests, ...payrollItems].filter(
      (r) => r.provenance === 'dataset_b_observed',
    ).length
    // Would have read "17 demo records / 1 observed" forever once payroll shipped.
    expect(page().getByText(new RegExp(`${total} demo records`))).toBeTruthy()
    expect(page().getByText(`${observed} observed`)).toBeTruthy()
  })

  it('quotes Phase 2 evidence from the workflow definitions', async () => {
    renderAt('/history')
    await waitFor(() => expect(page().getByText('Breakdown by workflow')).toBeTruthy(), settle)
    for (const w of workflows) {
      expect(
        page().getAllByText(String(w.evidence.observed_executions)).length,
      ).toBeGreaterThan(0)
    }
    // The stale claim that payroll was unbuilt must be gone.
    expect(page().queryByText(/workflow not implemented yet/)).toBeNull()
  })

  it('cites the segment belonging to its own workflow, not leave', async () => {
    renderAt('/execution/JOB-3001') // a payroll run
    await waitFor(() => expect(page().getByText(/Execution:/)).toBeTruthy(), settle)
    const payroll = workflows.find((w) => w.workflow === 'PAYROLL_CONFIRMATION')!
    await waitFor(
      () =>
        expect(
          page().getAllByText(payroll.evidence.clean_instance_segment_id).length,
        ).toBeGreaterThan(0),
      settle,
    )
    // ...and not the leave segment it used to hardcode.
    expect(page().queryByText('ses_20260701-180923-NEELA9BAF::seg013')).toBeNull()
  })
})

describe('prototype run metrics', () => {
  it('renders all five metrics with their real values', async () => {
    renderAt('/history')
    await waitFor(() => expect(page().getByText('Prototype run metrics')).toBeTruthy(), settle)

    expect(page().getByText('Automation success rate')).toBeTruthy()
    // "Verification" also labels a column in the run table below.
    expect(page().getAllByText('Verification').length).toBeGreaterThan(0)
    expect(page().getByText('Automation / review rate')).toBeTruthy()
    expect(page().getByText('Execution latency')).toBeTruthy()
    expect(page().getByText('Safety — policy bypasses')).toBeTruthy()
    expect(page().getByText('Safety — adversarial probe')).toBeTruthy()
  })

  it('shows the human baseline beside prototype latency, never subtracted', async () => {
    renderAt('/history')
    await waitFor(() => expect(page().getByText('Prototype run metrics')).toBeTruthy(), settle)

    expect(page().getByText(/NOT a savings figure/)).toBeTruthy()
    // Anchored to the Dataset B segments the baseline came from, which is the
    // durable fact - not a float's rounding.
    expect(page().getByText('ses_20260701-180923-NEELA9BAF::seg013')).toBeTruthy()
    expect(page().getByText('ses_20260701-190250-NEELA9BAF::seg002')).toBeTruthy()
    expect(page().getAllByText('Human clean instance').length).toBe(2)
    expect(page().getByText(/THIS IS NOT A SAVINGS FIGURE/)).toBeTruthy()
  })

  it('states that zero observed bypasses alone proves little', async () => {
    renderAt('/history')
    await waitFor(() => expect(page().getByText('Prototype run metrics')).toBeTruthy(), settle)
    expect(page().getByText(/proves little on its own/)).toBeTruthy()
    expect(page().getByText('Safety claim holds')).toBeTruthy()
  })
})

describe('mock data integrity', () => {
  it('mirrors the backend dataset exactly in size and provenance mix', () => {
    expect(leaveRequests.length).toBe(17)
    expect(leaveRequests.filter((r) => r.provenance === 'dataset_b_observed').length).toBe(1)
    expect(leaveRequests.filter((r) => r.provenance === 'dataset_b_list_observed').length).toBe(6)
    expect(leaveRequests.filter((r) => r.provenance === 'synthetic_demo').length).toBe(10)
  })

  it('keeps the grounded record faithful to the Dataset B screenshot', () => {
    const rec = leaveRequests.find((r) => r.record_id === 'P2-07048822-006')!
    expect(rec.employee_id).toBe('E2001')
    expect(rec.employee_name).toBe('青木 拓也')
    expect(rec.request_type).toBe('代休申請')
    expect(rec.request_date).toBe('2026-07-13')
    expect(rec.department).toBe('営業部')
    expect(rec.prior_approval_required).toBe(true)
    // Never fabricated: Dataset B never showed whether approval was obtained.
    expect(rec.prior_approval_obtained).toBeNull()
  })

  it('never lets a synthetic record wear an observed-looking id', () => {
    for (const rec of leaveRequests) {
      if (rec.provenance === 'synthetic_demo') expect(rec.record_id.startsWith('DEMO-')).toBe(true)
      else expect(rec.record_id.startsWith('DEMO-')).toBe(false)
    }
  })

  it('never routes a REVIEW decision without flagging human review', () => {
    for (const job of allJobs) {
      if (job.decision?.decision === 'REVIEW') {
        expect(job.decision.human_review_required).toBe(true)
      }
    }
  })
})
