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
  computeMetrics,
  decisionDistribution,
  jobs,
  leaveRequests,
  queueTasks,
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
  fetchQueue: async () => queueTasks,
  fetchJobs: async () => jobs,
  fetchJob: async (id: string) => {
    const found = jobs.find((j) => j.job_id === id)
    if (!found) throw new Error(`No job ${id}`)
    return found
  },
  fetchRunHistory: async () => runHistory,
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
  startLeaveAutomation: async (recordId: string) =>
    jobs.find((j) => (j.record as { record_id: string }).record_id === recordId) ?? jobs[0],
  submitHumanDecision: async (jobId: string) =>
    jobs.find((j) => j.job_id === jobId) ?? jobs[0],
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
    expect(page().getAllByRole('row').length).toBe(queueTasks.length + 1)
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
    const reviewCount = jobs.filter((j) => j.state === 'HUMAN_REVIEW').length
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
    expect(page().getAllByText('Unknown').length).toBeGreaterThan(0)
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
    for (const job of jobs) {
      if (job.decision?.decision === 'REVIEW') {
        expect(job.decision.human_review_required).toBe(true)
      }
    }
  })
})
