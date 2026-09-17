import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  Clock,
  Cpu,
  Gauge,
  Layers,
  PlugZap,
  Terminal,
  TriangleAlert,
  UserCheck,
} from 'lucide-react'
import { PageHeader } from '@/components/layout/AppShell'
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardHeader,
  Dot,
  ErrorState,
  LoadingState,
  Mono,
  StatCard,
  Table,
  Td,
  Th,
} from '@/components/ui'
import { Donut } from '@/components/charts'
import {
  DecisionBadge,
  DemoDataNotice,
  PipelineStrip,
  StateBadge,
} from '@/components/domain'
import { useAsync } from '@/hooks/useAsync'
import { fetchDashboard, fetchJobs, fetchWorkflows } from '@/services/api'
import { clockTime, pct, relativeTime, seconds } from '@/lib/format'
import type { AutomationJob, JobState } from '@/types'

export default function Dashboard() {
  const navigate = useNavigate()
  const dash = useAsync(fetchDashboard, [])
  const jobsQ = useAsync(fetchJobs, [])
  const flowsQ = useAsync(fetchWorkflows, [])

  if (dash.error) return <ErrorState message={dash.error} onRetry={dash.reload} />
  if (dash.loading || jobsQ.loading || flowsQ.loading || !dash.data || !jobsQ.data || !flowsQ.data) {
    return <LoadingState label="Loading operations overview…" />
  }

  const { metrics, decisions, connectors } = dash.data
  const jobs = jobsQ.data
  const workflows = flowsQ.data

  const stageCounts = jobs.reduce<Record<string, number>>((acc, j) => {
    acc[j.state] = (acc[j.state] ?? 0) + 1
    return acc
  }, {})
  stageCounts.LOADING = metrics.queued

  // The observed human clean-instance times, read from the workflow evidence
  // rather than typed in. Two workflows now, so it is a range, not one number.
  const cleanInstances = workflows
    .map((w) => w.evidence.clean_instance_duration_seconds)
    .filter((n): n is number => typeof n === 'number')
    .sort((a, b) => a - b)
  const humanBaseline = cleanInstances.length
    ? cleanInstances.length === 1
      ? `${cleanInstances[0].toFixed(1)}s`
      : `${cleanInstances[0].toFixed(1)}–${cleanInstances[cleanInstances.length - 1].toFixed(1)}s`
    : null

  const reviewJobs = jobs.filter((j) => j.state === 'HUMAN_REVIEW')
  const recent = [...jobs]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 6)

  return (
    <>
      <PageHeader
        title="Operations Overview"
        badge={
          <Badge tone="brand" dot pulse>
            Agent + executor live
          </Badge>
        }
        subtitle="Bounded workflow automation recovered from desktop operation logs. Every decision is traceable from Dataset B evidence through policy evaluation to verified execution."
        meta={
          <>
            <span>prototype v0.2</span>
            <span>·</span>
            <span>Policy: leave-approval-prototype-v1</span>
            <span>·</span>
            <span>Records loaded: {metrics.pendingRecords} pending</span>
          </>
        }
        actions={
          <>
            <Button variant="secondary" icon={<Terminal size={14} />} onClick={() => navigate('/queue')}>
              Open task queue
            </Button>
            <Button variant="dark" icon={<Cpu size={14} />} onClick={() => navigate('/agent')}>
              Review agent decision
            </Button>
          </>
        }
      />

      <div className="mb-5">
        <DemoDataNotice />
      </div>

      {/* Pipeline */}
      <Card className="mb-5">
        <CardHeader
          title="Deterministic pipeline"
          subtitle="Python owns every transition. The LLM decides; it never drives the browser."
          icon={<Layers size={16} />}
          action={
            <span className="font-mono text-[11.5px] text-ink-400">
              state ≠ decision · 10 states
            </span>
          }
        />
        <div className="mt-4">
          <PipelineStrip
            counts={stageCounts as Record<JobState, number>}
            sublabels={{
              LOADING: 'records queued',
              VALIDATING: 'field completeness',
              ANALYZING: 'field extraction',
              POLICY_CHECK: 'policy gates',
              EXECUTING: 'browser actions',
              VERIFYING: 'status confirmed',
            }}
          />
        </div>
      </Card>

      {/* KPIs */}
      <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Records in scope"
          value={metrics.pendingRecords}
          icon={<BookOpenCheck size={15} />}
          footnote={
            <>
              {metrics.totalRecords} demo records ·{' '}
              <span className="text-ok-700 font-semibold">{metrics.observedRecords} observed</span>{' '}
              in Dataset B
            </>
          }
        />
        <StatCard
          label="Auto-decided"
          value={pct(metrics.autonomousRate, 0)}
          delta={`${metrics.totalJobs} jobs`}
          deltaTone="brand"
          icon={<Gauge size={15} />}
          footnote="Share of jobs the policy resolved without a human"
        />
        <StatCard
          label="Avg execution"
          value={seconds(metrics.avgExecutionSeconds)}
          icon={<Clock size={15} />}
          footnote={
            humanBaseline ? (
              <>
                Human baseline: <span className="tnum">{humanBaseline}</span> observed clean
                instance
              </>
            ) : (
              'Human baseline: see workflow evidence'
            )
          }
        />
        <StatCard
          label="Awaiting human"
          value={metrics.humanReview}
          delta={metrics.humanReview > 0 ? 'action needed' : 'clear'}
          deltaTone={metrics.humanReview > 0 ? 'warn' : 'ok'}
          icon={<UserCheck size={15} />}
          footnote="Escalated because policy could not decide"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          {/* Workflows */}
          <Card>
            <CardHeader
              title="Automated workflows"
              subtitle="Evidence figures below are real Phase 2 measurements from Dataset B, not prototype output."
              icon={<Layers size={16} />}
            />
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {workflows.map((wf) => (
                <div key={wf.workflow} className="rounded-lg border border-line bg-surface-sunken p-4">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-[13.5px] font-bold text-ink-900">{wf.name}</h3>
                    <Badge tone={wf.implemented ? 'ok' : 'warn'} dot>
                      {wf.implemented ? 'Workflow #1' : 'Declared'}
                    </Badge>
                  </div>
                  <p className="mt-1.5 text-[12px] leading-snug text-ink-500">{wf.description}</p>
                  <div className="mt-3 grid grid-cols-2 gap-3 border-t border-line pt-3">
                    <div>
                      <p className="label-xs text-ink-400">Observed executions</p>
                      <p className="mt-0.5 text-[16px] font-bold tnum text-ink-900">
                        {wf.evidence.observed_executions}
                      </p>
                    </div>
                    <div>
                      <p className="label-xs text-ink-400">Observed minutes</p>
                      <p className="mt-0.5 text-[16px] font-bold tnum text-ink-900">
                        {wf.evidence.observed_minutes}
                      </p>
                    </div>
                  </div>
                  <p className="mt-2.5 flex items-center gap-1.5 font-mono text-[10.5px] text-ink-400">
                    <CheckCircle2 size={11} className="text-ok-500" />
                    {wf.evidence.clean_instance_segment_id.slice(0, 34)}…
                  </p>
                </div>
              ))}
            </div>
          </Card>

          {/* Decision stream */}
          <Card padded={false}>
            <div className="flex items-center justify-between p-5 pb-3">
              <CardHeader
                title="Recent agent decisions"
                subtitle="Most recent jobs, newest first"
                icon={<Cpu size={16} />}
              />
              <Link
                to="/history"
                className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-brand-600 hover:text-brand-700"
              >
                Full history <ArrowRight size={13} />
              </Link>
            </div>
            <Table>
              <thead>
                <tr>
                  <Th>Time</Th>
                  <Th>Job</Th>
                  <Th>Subject</Th>
                  <Th>Decision</Th>
                  <Th>State</Th>
                  <Th align="right">Exec</Th>
                </tr>
              </thead>
              <tbody>
                {recent.map((job: AutomationJob) => {
                  const rec = job.record
                  return (
                    <tr
                      key={job.job_id}
                      className="cursor-pointer transition-colors hover:bg-surface-sunken"
                      onClick={() => navigate(`/agent/${job.job_id}`)}
                    >
                      <Td>
                        <Mono className="text-ink-400">{clockTime(job.updated_at)}</Mono>
                      </Td>
                      <Td>
                        <Mono className="font-semibold text-brand-600">{job.job_id}</Mono>
                      </Td>
                      <Td>
                        <span className="flex items-center gap-2">
                          <Avatar name={rec.employee_name} size="sm" />
                          <span>
                            <span className="block font-semibold text-ink-900">
                              {rec.employee_name ?? '—'}
                            </span>
                            <Mono className="text-[10.5px] text-ink-400">{rec.record_id}</Mono>
                          </span>
                        </span>
                      </Td>
                      <Td>
                        {job.decision ? (
                          <DecisionBadge
                            decision={job.decision.decision}
                            confidence={job.decision.confidence}
                          />
                        ) : (
                          <span className="text-ink-300">—</span>
                        )}
                      </Td>
                      <Td>
                        <StateBadge
                          state={job.state}
                          pulse={job.state === 'EXECUTING' || job.state === 'VERIFYING'}
                        />
                      </Td>
                      <Td align="right">
                        <Mono className="text-ink-500">
                          {seconds(job.execution?.duration_seconds)}
                        </Mono>
                      </Td>
                    </tr>
                  )
                })}
              </tbody>
            </Table>
          </Card>
        </div>

        {/* Right rail */}
        <div className="space-y-5">
          <Card>
            <CardHeader
              title="Needs human review"
              subtitle="Policy could not decide these"
              icon={<TriangleAlert size={16} />}
              action={<Badge tone="warn">{reviewJobs.length} queued</Badge>}
            />
            <div className="mt-4 space-y-3">
              {reviewJobs.slice(0, 3).map((job) => {
                const rec = job.record
                return (
                  <div key={job.job_id} className="rounded-lg border border-line bg-surface-sunken p-3.5">
                    <div className="flex items-start gap-2.5">
                      <Avatar name={rec.employee_name} size="sm" />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-[12.5px] font-bold text-ink-900">
                            {rec.employee_name ?? rec.record_id}
                          </p>
                          <Badge tone="warn" className="shrink-0">
                            {job.decision?.ambiguity_type?.replace(/_/g, ' ').toLowerCase() ?? 'review'}
                          </Badge>
                        </div>
                        <p className="mt-1 line-clamp-2 text-[11.5px] leading-snug text-ink-500">
                          {job.decision?.reason}
                        </p>
                        <div className="mt-2 flex items-center justify-between">
                          <Mono className="text-[10.5px] text-ink-400">
                            {relativeTime(job.updated_at)}
                          </Mono>
                          <Button
                            size="sm"
                            variant="dark"
                            onClick={() => navigate(`/review/${job.job_id}`)}
                          >
                            Review
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>

          <Card>
            <CardHeader title="Decision distribution" subtitle="Across all decided jobs" />
            <div className="mt-4 flex items-center gap-5">
              <Donut
                segments={[
                  { label: 'Approve', value: decisions.approve, color: 'var(--color-brand-600)' },
                  { label: 'Review', value: decisions.review, color: 'var(--color-warn-500)' },
                  { label: 'Reject', value: decisions.reject, color: 'var(--color-risk-500)' },
                ]}
                centerValue={pct(decisions.total ? decisions.approve / decisions.total : 0, 0)}
                centerLabel="auto-approved"
              />
              <ul className="flex-1 space-y-2.5">
                {[
                  { label: 'Auto-approved', value: decisions.approve, tone: 'brand' as const },
                  { label: 'Needs review', value: decisions.review, tone: 'warn' as const },
                  { label: 'Auto-rejected', value: decisions.reject, tone: 'risk' as const },
                ].map((row) => (
                  <li key={row.label} className="flex items-center justify-between text-[12.5px]">
                    <span className="flex items-center gap-2 text-ink-500">
                      <Dot tone={row.tone} />
                      {row.label}
                    </span>
                    <span className="tnum font-semibold text-ink-900">{row.value}</span>
                  </li>
                ))}
              </ul>
            </div>
            <p className="mt-3 border-t border-line pt-3 font-mono text-[10.5px] leading-snug text-ink-400">
              Auto-rejection is disabled by policy — the 差戻し path was never observed in Dataset B.
            </p>
          </Card>

          <Card>
            <CardHeader title="System connectors" icon={<PlugZap size={16} />} />
            <ul className="mt-3.5 space-y-2.5">
              {connectors.map((c) => (
                <li key={c.name} className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[12.5px] font-semibold text-ink-900">{c.name}</p>
                    <Mono className="text-[10.5px] text-ink-400">{c.detail}</Mono>
                  </div>
                  <Badge tone={c.status === 'connected' ? 'ok' : 'neutral'} dot>
                    {c.status === 'connected' ? 'Live' : 'Planned'}
                  </Badge>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </>
  )
}
