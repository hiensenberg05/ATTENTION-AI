import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Activity,
  CheckCircle2,
  Download,
  FileClock,
  Search,
  ShieldCheck,
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
  EmptyState,
  ErrorState,
  LoadingState,
  Mono,
  StatCard,
  Table,
  Tabs,
  Td,
  Th,
} from '@/components/ui'
import { Donut, StackedBars } from '@/components/charts'
import { DecisionBadge, DemoDataNotice } from '@/components/domain'
import { PrototypeMetricsPanel } from '@/components/domain/PrototypeMetricsPanel'
import { useAsync } from '@/hooks/useAsync'
import {
  fetchDashboard,
  fetchPrototypeMetrics,
  fetchRunHistory,
  fetchWorkflows,
} from '@/services/api'
import { clockTime, ms, pct, relativeTime, seconds, shortDate } from '@/lib/format'

type TabId = 'all' | 'approved' | 'review' | 'overridden' | 'failed'

export default function AuditHistory() {
  const navigate = useNavigate()
  const runsQ = useAsync(fetchRunHistory, [])
  const dashQ = useAsync(fetchDashboard, [])
  const flowsQ = useAsync(fetchWorkflows, [])
  const metricsQ = useAsync(fetchPrototypeMetrics, [])
  const [tab, setTab] = useState<TabId>('all')
  const [query, setQuery] = useState('')

  // Hooks must run on every render — compute before any early return.
  const allRuns = useMemo(() => runsQ.data ?? [], [runsQ.data])
  const byWorkflow = useMemo(() => {
    const leave = allRuns.filter((r) => r.workflow === 'LEAVE_APPROVAL').length
    const payroll = allRuns.filter((r) => r.workflow === 'PAYROLL_CONFIRMATION').length
    return { leave, payroll, total: allRuns.length }
  }, [allRuns])

  if (runsQ.error) return <ErrorState message={runsQ.error} onRetry={runsQ.reload} />
  if (runsQ.loading || dashQ.loading || !runsQ.data || !dashQ.data) {
    return <LoadingState label="Loading audit trail…" />
  }

  // Everything Phase 2 measured, read from the workflow definitions the backend
  // serves. Nothing on this screen restates an evidence figure from memory.
  const definitions = flowsQ.data ?? []
  const evidence = definitions.map((w) => ({
    workflow: w.workflow,
    label: w.workflow === 'LEAVE_APPROVAL' ? 'leave' : 'payroll',
    executions: w.evidence.observed_executions,
    minutes: w.evidence.observed_minutes,
    cleanInstance: w.evidence.clean_instance_duration_seconds,
  }))
  const cleanInstances = evidence
    .map((e) => e.cleanInstance)
    .filter((n): n is number => typeof n === 'number')
    .sort((a, b) => a - b)
  const humanBaseline = cleanInstances.length
    ? cleanInstances.length === 1
      ? `${cleanInstances[0].toFixed(1)}s`
      : `${cleanInstances[0].toFixed(1)}–${cleanInstances[cleanInstances.length - 1].toFixed(1)}s`
    : null
  const payrollDef = definitions.find((w) => w.workflow === 'PAYROLL_CONFIRMATION')
  const payrollEvidence = payrollDef
    ? `${payrollDef.evidence.observed_executions} observed in Dataset B`
    : 'workflow not implemented yet'

  const runs = runsQ.data
  const { metrics, throughput } = dashQ.data

  const counts = {
    all: runs.length,
    approved: runs.filter((r) => r.decision === 'APPROVE' && !r.human_overridden).length,
    review: runs.filter((r) => r.decision === 'REVIEW').length,
    overridden: runs.filter((r) => r.human_overridden).length,
    failed: runs.filter((r) => r.verification_status === 'FAILED').length,
  }

  const filtered = runs.filter((r) => {
    if (tab === 'approved' && !(r.decision === 'APPROVE' && !r.human_overridden)) return false
    if (tab === 'review' && r.decision !== 'REVIEW') return false
    if (tab === 'overridden' && !r.human_overridden) return false
    if (tab === 'failed' && r.verification_status !== 'FAILED') return false
    if (query) {
      const hay = `${r.run_id} ${r.subject} ${r.subject_detail} ${r.workflow}`.toLowerCase()
      if (!hay.includes(query.toLowerCase())) return false
    }
    return true
  })

  const verifiedRuns = runs.filter((r) => r.verification_status === 'VERIFIED').length
  const avgMs = runs.reduce((a, r) => a + r.duration_ms, 0) / (runs.length || 1)

  return (
    <>
      <PageHeader
        title="Audit &amp; Run History"
        badge={<Badge tone="brand" dot>Every run recorded</Badge>}
        subtitle="Complete log of policy evaluations, executions and human determinations. Each run keeps its decision, its verification outcome and the state path it took."
        meta={
          <>
            <span>{runs.length} runs</span>
            <span>·</span>
            <span>Retention: prototype session</span>
            <span>·</span>
            <span>Policy leave-approval-prototype-v1</span>
          </>
        }
        actions={
          <>
            <select className="rounded-lg border border-line bg-surface px-3 py-2 text-[12.5px] font-medium text-ink-700 focus:border-brand-400 focus:outline-none">
              <option>Last 30 days</option>
              <option>Last 7 days</option>
              <option>Today</option>
            </select>
            <Button variant="dark" icon={<Download size={14} />}>
              Export audit report
            </Button>
          </>
        }
      />

      {/* The five metrics that go in the report, computed backend-side. */}
      {metricsQ.data && (
        <div className="mb-5">
          <PrototypeMetricsPanel m={metricsQ.data} />
        </div>
      )}

      <div className="mb-5">
        <DemoDataNotice>
          <strong className="font-bold">Live run history.</strong> Every row is a real run against
          the mock HR system, with a measured duration — never an estimate. The trail is held in
          memory, so restarting the backend clears it.
        </DemoDataNotice>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Total runs" value={runs.length} icon={<Activity size={15} />} footnote="Across both workflows" />
        <StatCard
          label="Auto-decided"
          value={pct(counts.all ? counts.approved / counts.all : 0, 1)}
          icon={<CheckCircle2 size={15} />}
          footnote={`${counts.approved} resolved without a human`}
        />
        <StatCard
          label="Human involved"
          value={counts.overridden + counts.review}
          icon={<UserCheck size={15} />}
          footnote="Escalations plus operator overrides"
        />
        <StatCard
          label="Verified"
          value={pct(runs.length ? verifiedRuns / runs.length : 0, 1)}
          icon={<ShieldCheck size={15} />}
          footnote="Status change confirmed after execution"
        />
        <StatCard
          label="Avg duration"
          value={ms(Math.round(avgMs))}
          icon={<FileClock size={15} />}
          footnote={
            humanBaseline ? (
              <>
                Observed human clean instance: <span className="tnum">{humanBaseline}</span>
              </>
            ) : (
              'Observed human clean instance: see workflow evidence'
            )
          }
        />
      </div>

      <div className="mb-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
        <Card>
          <CardHeader
            title="Autonomous resolution vs human intervention"
            subtitle="30-day throughput — demo series"
            action={
              <div className="flex items-center gap-3 text-[11.5px] text-ink-500">
                <span className="flex items-center gap-1.5">
                  <Dot tone="brand" /> Autonomous
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-brand-200" /> Human
                </span>
              </div>
            }
          />
          <div className="mt-5">
            <StackedBars data={throughput} />
          </div>
          <div className="mt-2 flex justify-between font-mono text-[10.5px] text-ink-400">
            <span>30 days ago</span>
            <span>mid-period</span>
            <span>today</span>
          </div>
        </Card>

        <Card>
          <CardHeader title="Breakdown by workflow" subtitle={`${runs.length} runs total`} />
          <div className="mt-4 flex items-center gap-5">
            <Donut
              segments={[
                { label: 'Leave', value: byWorkflow.leave, color: 'var(--color-brand-600)' },
                { label: 'Payroll', value: byWorkflow.payroll, color: 'var(--color-brand-200)' },
              ]}
              centerValue="2"
              centerLabel="workflows"
            />
            <ul className="flex-1 space-y-3">
              <li>
                <div className="flex items-center justify-between text-[12.5px]">
                  <span className="flex items-center gap-2 text-ink-700">
                    <Dot tone="brand" /> Leave Approval
                  </span>
                  <span className="tnum font-semibold">
                    {pct(byWorkflow.total ? byWorkflow.leave / byWorkflow.total : 0, 0)}
                  </span>
                </div>
                <p className="mt-0.5 text-[11px] text-ink-400">{byWorkflow.leave} runs</p>
              </li>
              <li>
                <div className="flex items-center justify-between text-[12.5px]">
                  <span className="flex items-center gap-2 text-ink-700">
                    <span className="h-2 w-2 rounded-full bg-brand-200" /> Payroll Confirmation
                  </span>
                  <span className="tnum font-semibold">
                    {pct(byWorkflow.total ? byWorkflow.payroll / byWorkflow.total : 0, 0)}
                  </span>
                </div>
                <p className="mt-0.5 text-[11px] text-ink-400">
                  {byWorkflow.payroll} runs · {payrollEvidence}
                </p>
              </li>
            </ul>
          </div>
          <p className="mt-4 border-t border-line pt-3 text-[11.5px] leading-snug text-ink-500">
            Phase 2 measured{' '}
            {evidence.map((e, i) => (
              <span key={e.workflow}>
                {i > 0 && ' and '}
                <span className="tnum font-semibold">{e.executions}</span> {e.label.toLowerCase()}
              </span>
            ))}{' '}
            executions in Dataset B — those are the real observations that justified building
            these two workflows. They measure what <em>people</em> did, and are never mixed with
            the prototype run counts above.
          </p>
        </Card>
      </div>

      <Card padded={false}>
        <div className="flex flex-wrap items-center gap-3 border-b border-line p-4">
          <Tabs<TabId>
            active={tab}
            onChange={setTab}
            tabs={[
              { id: 'all', label: 'All runs', count: counts.all },
              { id: 'approved', label: 'Auto-approved', count: counts.approved, tone: 'ok' },
              { id: 'review', label: 'Escalated', count: counts.review, tone: 'warn' },
              { id: 'overridden', label: 'Human override', count: counts.overridden, tone: 'info' },
              { id: 'failed', label: 'Failed verification', count: counts.failed, tone: 'risk' },
            ]}
          />
          <div className="relative ml-auto min-w-[220px] flex-1 lg:max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by run ID or subject…"
              className="w-full rounded-lg border border-line bg-canvas py-2 pl-9 pr-3 text-[12.5px] focus:border-brand-400 focus:bg-surface focus:outline-none"
            />
          </div>
        </div>

        {filtered.length === 0 ? (
          <EmptyState title="No runs match" detail="Try a different tab or clear the search." />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Run</Th>
                <Th>When</Th>
                <Th>Workflow &amp; subject</Th>
                <Th>Decision</Th>
                <Th>Systems</Th>
                <Th>Verification</Th>
                <Th align="right">Duration</Th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((run) => (
                <tr
                  key={run.run_id}
                  onClick={() => navigate(`/agent/${run.job_id}`)}
                  className="cursor-pointer transition-colors hover:bg-surface-sunken"
                >
                  <Td>
                    <Mono className="font-semibold text-brand-600">{run.run_id}</Mono>
                  </Td>
                  <Td>
                    <Mono className="block text-[11.5px] text-ink-700">
                      {clockTime(run.timestamp)}
                    </Mono>
                    <span className="text-[11px] text-ink-400">{relativeTime(run.timestamp)}</span>
                  </Td>
                  <Td>
                    <span className="flex items-center gap-2.5">
                      <Avatar name={run.subject} size="sm" />
                      <span className="min-w-0">
                        <span className="block font-semibold text-ink-900">{run.subject}</span>
                        <Mono className="block text-[10.5px] text-ink-400">
                          {run.subject_detail}
                        </Mono>
                      </span>
                    </span>
                  </Td>
                  <Td>
                    <span className="flex items-center gap-2">
                      <DecisionBadge decision={run.decision} />
                      {run.human_overridden && <Badge tone="info">human</Badge>}
                    </span>
                  </Td>
                  <Td>
                    <span className="flex flex-wrap gap-1">
                      {run.systems_touched.slice(0, 2).map((s) => (
                        <span
                          key={s}
                          className="rounded border border-line bg-canvas px-1.5 py-0.5 font-mono text-[10px] text-ink-500"
                        >
                          {s}
                        </span>
                      ))}
                    </span>
                  </Td>
                  <Td>
                    <Badge
                      tone={
                        run.verification_status === 'VERIFIED'
                          ? 'ok'
                          : run.verification_status === 'FAILED'
                            ? 'risk'
                            : 'neutral'
                      }
                      dot
                    >
                      {run.verification_status.toLowerCase()}
                    </Badge>
                  </Td>
                  <Td align="right">
                    <Mono className="text-ink-500">{ms(run.duration_ms)}</Mono>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}

        <div className="flex items-center justify-between border-t border-line px-4 py-3">
          <p className="text-[12px] text-ink-400">
            Showing <span className="tnum font-semibold text-ink-700">{filtered.length}</span> of{' '}
            <span className="tnum">{runs.length}</span> runs
          </p>
          <p className="font-mono text-[11px] text-ink-400">
            avg {seconds(avgMs / 1000)} · {metrics.completed} completed
          </p>
        </div>
      </Card>

      <Card className="mt-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 text-brand-600">
              <TriangleAlert size={17} />
            </span>
            <div>
              <h3 className="text-[13.5px] font-bold text-ink-900">
                What this audit trail is, and is not
              </h3>
              <p className="mt-1.5 max-w-3xl text-[12px] leading-snug text-ink-500">
                Once the agent and executor stages land, every row here records a real run: the
                decision the policy produced, the deterministic actions taken, and whether the
                record's status actually changed. Until then these are demo rows. The prototype
                keeps historical Phase 2 evidence and live run metrics as separate things on
                purpose — conflating them would present measured observations and prototype output
                as the same kind of number.
              </p>
            </div>
          </div>
          <Mono className="text-[11px] text-ink-400">
            session started {shortDate(new Date().toISOString())}
          </Mono>
        </div>
      </Card>
    </>
  )
}
