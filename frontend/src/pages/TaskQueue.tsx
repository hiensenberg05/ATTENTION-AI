import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Clock,
  Download,
  Filter,
  Gauge,
  ListChecks,
  RefreshCw,
  Search,
  ShieldAlert,
  Play,
  Zap,
} from 'lucide-react'
import { PageHeader } from '@/components/layout/AppShell'
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  IdChip,
  LoadingState,
  Mono,
  StatCard,
  Table,
  Tabs,
  Td,
  Th,
} from '@/components/ui'
import { cx } from '@/components/ui'
import { MiniRing } from '@/components/charts'
import { DemoDataNotice, ProvenanceBadge, StageBadge } from '@/components/domain'
import { useAsync } from '@/hooks/useAsync'
import { fetchQueue, startAutomation } from '@/services/api'
import { isPending, searchableText, WORKFLOW_LABEL } from '@/lib/record'
import { pct, relativeTime, seconds } from '@/lib/format'
import type { QueueTask } from '@/types'

type TabId = 'all' | 'leave' | 'payroll' | 'review' | 'failed'

export default function TaskQueue() {
  const navigate = useNavigate()
  const { data, loading, error, reload } = useAsync(fetchQueue, [])
  const [tab, setTab] = useState<TabId>('all')
  const [query, setQuery] = useState('')
  const [stageFilter, setStageFilter] = useState<string>('all')
  const [running, setRunning] = useState<string | null>(null)
  const [runError, setRunError] = useState<string | null>(null)
  const [bulk, setBulk] = useState<{ done: number; total: number } | null>(null)
  // A plain ref, not state: the loop below reads it between iterations and must
  // see the current value, not the one captured when the run started.
  const cancelBulk = useRef(false)
  const [bulkSummary, setBulkSummary] = useState<{
    approved: number
    escalated: number
    failed: number
    cancelled: boolean
  } | null>(null)

  // Memoised so the filter/count memos below have a stable dependency.
  const tasks = useMemo(() => data ?? [], [data])

  const filtered = useMemo(() => {
    return tasks.filter((t) => {
      if (tab === 'leave' && t.workflow !== 'LEAVE_APPROVAL') return false
      if (tab === 'payroll' && t.workflow !== 'PAYROLL_CONFIRMATION') return false
      if (tab === 'review' && t.stage !== 'Pending Human Sign-off') return false
      if (tab === 'failed' && t.stage !== 'Failed') return false
      if (stageFilter !== 'all' && t.stage !== stageFilter) return false
      if (query) {
        const rec = t.record
        const haystack = [
          searchableText(rec),
          t.task_id,
        ]
          .join(' ')
          .toLowerCase()
        if (!haystack.includes(query.toLowerCase())) return false
      }
      return true
    })
  }, [tasks, tab, query, stageFilter])

  const counts = useMemo(
    () => ({
      all: tasks.length,
      leave: tasks.filter((t) => t.workflow === 'LEAVE_APPROVAL').length,
      payroll: tasks.filter((t) => t.workflow === 'PAYROLL_CONFIRMATION').length,
      review: tasks.filter((t) => t.stage === 'Pending Human Sign-off').length,
      failed: tasks.filter((t) => t.stage === 'Failed').length,
      queued: tasks.filter((t) => t.stage === 'Queued').length,
      evaluating: tasks.filter((t) => t.stage === 'Agent Evaluating').length,
      // Only tasks that actually reached a decision may appear in a rate.
      decided: tasks.filter((t) => t.decision !== null).length,
      autoDecided: tasks.filter((t) => t.decision !== null && t.decision !== 'REVIEW').length,
      durations: tasks
        .map((t) => t.duration_seconds)
        .filter((d): d is number => typeof d === 'number' && d > 0),
    }),
    [tasks],
  )

  if (error) return <ErrorState message={error} onRetry={reload} />

  function openTask(task: QueueTask) {
    // A record nobody has run yet has no job to open - run it first.
    if (!task.job_id) return
    if (task.stage === 'Pending Human Sign-off') navigate(`/review/${task.job_id}`)
    else if (['Executing', 'Verifying', 'Completed', 'Failed'].includes(task.stage))
      navigate(`/execution/${task.job_id}`)
    else navigate(`/agent/${task.job_id}`)
  }

  /**
   * Run one record through the pipeline and go to whichever screen the outcome
   * belongs on. The request resolves only when the run has finished, so the
   * button stays busy for the real duration rather than for a fixed animation.
   */
  async function runTask(task: QueueTask) {
    const recordId = task.record.record_id
    setRunning(recordId)
    setRunError(null)
    try {
      const job = await startAutomation(task.workflow, recordId)
      await reload()
      navigate(job.state === 'HUMAN_REVIEW' ? `/review/${job.job_id}` : `/execution/${job.job_id}`)
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err))
    } finally {
      setRunning(null)
    }
  }

  /**
   * Run every pending record that has not been run yet, one at a time.
   *
   * Sequential on purpose: the backend holds a process-wide browser lock, so
   * firing these in parallel would just queue them server-side with no progress
   * to show. Running them here means the counter advances as each one lands.
   *
   * Expect roughly a minute or two for a full queue. The cost is Groq's rate
   * limiting, not our pipeline: the first decision returns in well under a
   * second, then the client backs off as the limit bites. Measured per-record
   * work is ~1s for an escalation and ~2s for an executed approval. Hence the
   * cancel control - the operator should never be trapped waiting on someone
   * else's quota.
   *
   * This exists because the queue's natural order buries the working path - the
   * seven observed Dataset B records all escalate, for good evidence-based
   * reasons, so clicking from the top looks like auto-approval is broken. Running
   * the whole queue shows the real split instead of the first seven rows of it.
   */
  async function runAllPending() {
    const pending = tasks.filter((t) => !t.job_id && isPending(t.record))
    if (pending.length === 0) return

    setRunError(null)
    setBulkSummary(null)
    setBulk({ done: 0, total: pending.length })

    cancelBulk.current = false
    const tally = { approved: 0, escalated: 0, failed: 0 }
    for (const [i, task] of pending.entries()) {
      if (cancelBulk.current) break
      try {
        const job = await startAutomation(task.workflow, task.record.record_id)
        if (job.state === 'HUMAN_REVIEW') tally.escalated += 1
        else if (job.state === 'COMPLETED') tally.approved += 1
        else tally.failed += 1
      } catch {
        // One bad record must not abandon the rest of the queue.
        tally.failed += 1
      }
      setBulk({ done: i + 1, total: pending.length })
    }

    const cancelled = cancelBulk.current
    cancelBulk.current = false
    setBulk(null)
    setBulkSummary({ ...tally, cancelled })
    await reload()
  }

  const pendingUnrun = tasks.filter((t) => !t.job_id && isPending(t.record)).length

  return (
    <>
      <PageHeader
        title="Workflow Task Queue"
        badge={<Badge tone="brand" dot>Leave Approval active</Badge>}
        subtitle="Business records queued for policy evaluation and dispatch. Clicking a task opens wherever it currently sits in the pipeline."
        actions={
          <>
            <Button variant="secondary" icon={<Filter size={14} />}>
              Filter by workflow
            </Button>
            <Button variant="secondary" icon={<Download size={14} />}>
              Export CSV
            </Button>
            {bulk && (
              <Button variant="secondary" onClick={() => (cancelBulk.current = true)}>
                Stop after this one
              </Button>
            )}
            <Button
              variant="dark"
              icon={<Zap size={14} />}
              disabled={bulk !== null || running !== null || pendingUnrun === 0}
              onClick={() => void runAllPending()}
              title={
                pendingUnrun === 0
                  ? 'Every pending record has already been run'
                  : `Run all ${pendingUnrun} un-run pending records. Takes a minute or two — the agent is rate-limited by the Groq API, not by the pipeline.`
              }
            >
              {bulk
                ? `Running ${bulk.done} of ${bulk.total}…`
                : `Run all pending${pendingUnrun ? ` (${pendingUnrun})` : ''}`}
            </Button>
          </>
        }
      />

      <div className="mb-5">
        <DemoDataNotice>
          <strong className="font-bold">Live queue.</strong> Records are read from the mock HR
          system, and their status changes as runs complete. Stages reflect real jobs: a record
          nobody has run yet is <span className="font-mono">Queued</span>.
        </DemoDataNotice>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Not yet run"
          value={counts.queued}
          icon={<ListChecks size={15} />}
          footnote={`${counts.decided} of ${counts.all} records have a decision`}
        />
        <StatCard
          label="Auto-decided share"
          value={counts.decided ? pct(counts.autoDecided / counts.decided, 1) : '—'}
          icon={<Gauge size={15} />}
          footnote={
            counts.decided
              ? `${counts.autoDecided} of ${counts.decided} decided without a human`
              : 'No record has been evaluated yet'
          }
          visual={
            counts.decided ? (
              <MiniRing
                value={counts.autoDecided / counts.decided}
                label={`${counts.autoDecided}/${counts.decided}`}
              />
            ) : undefined
          }
        />
        <StatCard
          label="Avg execution"
          value={
            counts.durations.length
              ? seconds(counts.durations.reduce((a, b) => a + b, 0) / counts.durations.length)
              : '—'
          }
          icon={<Clock size={15} />}
          footnote={
            counts.durations.length
              ? `Measured across ${counts.durations.length} executed run${counts.durations.length === 1 ? '' : 's'}`
              : 'Nothing has reached the browser yet'
          }
        />
        <StatCard
          label="Human escalations"
          value={counts.review}
          delta={counts.review > 0 ? 'action needed' : 'clear'}
          deltaTone={counts.review > 0 ? 'warn' : 'ok'}
          icon={<ShieldAlert size={15} />}
          footnote="Ambiguous or policy-uncovered records"
        />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Tabs<TabId>
          active={tab}
          onChange={setTab}
          tabs={[
            { id: 'all', label: 'All tasks', count: counts.all },
            { id: 'leave', label: 'Leave Approval', count: counts.leave, tone: 'brand' },
            { id: 'payroll', label: 'Payroll Confirmation', count: counts.payroll, tone: 'neutral' },
            { id: 'review', label: 'Needs review', count: counts.review, tone: 'warn' },
            { id: 'failed', label: 'Failed verification', count: counts.failed, tone: 'risk' },
          ]}
        />
      </div>

      <Card padded={false} className="overflow-hidden">
        <div className="flex flex-wrap items-center gap-3 border-b border-line p-4">
          <div className="relative min-w-[240px] flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by employee, record ID, department…"
              className="w-full rounded-lg border border-line bg-canvas py-2 pl-9 pr-3 text-[12.5px] focus:border-brand-400 focus:bg-surface focus:outline-none"
            />
          </div>
          <select
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
            className="rounded-lg border border-line bg-surface px-3 py-2 text-[12.5px] font-medium text-ink-700 focus:border-brand-400 focus:outline-none"
          >
            <option value="all">Stage: all</option>
            <option value="Queued">Queued</option>
            <option value="Agent Evaluating">Agent evaluating</option>
            <option value="Pending Human Sign-off">Pending human sign-off</option>
            <option value="Executing">Executing</option>
            <option value="Completed">Completed</option>
            <option value="Failed">Failed</option>
          </select>
          <Button variant="ghost" size="sm" icon={<RefreshCw size={13} />} onClick={reload}>
            Refresh
          </Button>
        </div>

        {bulkSummary && (
          <div className="mx-4 mb-3 rounded-lg border border-line bg-surface-sunken px-3.5 py-2.5 text-[12px] text-ink-600">
            <strong className="font-semibold text-ink-900">
              {bulkSummary.cancelled ? 'Queue run stopped.' : 'Queue run complete.'}
            </strong>{' '}
            <span className="font-semibold text-ok-700">{bulkSummary.approved} auto-approved</span>{' '}
            and executed without a human ·{' '}
            <span className="font-semibold text-warn-700">{bulkSummary.escalated} escalated</span>{' '}
            to human review
            {bulkSummary.failed > 0 && (
              <>
                {' '}· <span className="font-semibold text-risk-700">{bulkSummary.failed} failed</span>
              </>
            )}
            . Records escalate when a policy gate could not be evaluated — the observed Dataset B
            records lack the prior-approval field the policy needs, which is the honest result, not
            a failure.
          </div>
        )}

        {runError && (
          <div className="mx-4 mb-3 rounded-lg border border-risk-200 bg-risk-50 px-3.5 py-2.5 text-[12px] text-risk-700">
            <strong className="font-semibold">Run failed.</strong> {runError}
          </div>
        )}

        {loading ? (
          <LoadingState label="Loading queue…" />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No tasks match these filters"
            detail="Try clearing the search box or switching back to All tasks."
          />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th className="w-10" />
                <Th>Task</Th>
                <Th>Employee</Th>
                <Th>Workflow</Th>
                <Th>Requested</Th>
                <Th>Provenance</Th>
                <Th>Stage</Th>
                <Th className="w-28 text-right">Run</Th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((task) => {
                const rec = task.record
                return (
                  <tr
                    key={task.task_id}
                    onClick={() => openTask(task)}
                    className="cursor-pointer transition-colors hover:bg-surface-sunken"
                  >
                    <Td>
                      <input
                        type="checkbox"
                        onClick={(e) => e.stopPropagation()}
                        className="h-3.5 w-3.5 rounded border-line-strong accent-brand-600"
                        aria-label={`Select ${task.task_id}`}
                      />
                    </Td>
                    <Td>
                      <IdChip tone={task.stage === 'Failed' ? 'risk' : 'brand'}>
                        {task.task_id}
                      </IdChip>
                      <Mono className="mt-1 block text-[10.5px] text-ink-400">
                        {rec.record_id}
                      </Mono>
                    </Td>
                    <Td>
                      <span className="flex items-center gap-2.5">
                        <Avatar name={rec.employee_name} size="sm" />
                        <span className="min-w-0">
                          <span className="block font-semibold text-ink-900">
                            {rec.employee_name ?? '—'}
                          </span>
                          <span className="block text-[11px] text-ink-400">
                            {rec.employee_id ?? (
                              <span className="text-risk-500">employee_id missing</span>
                            )}
                          </span>
                        </span>
                      </span>
                    </Td>
                    <Td>
                      <span className="flex items-center gap-2">
                        <span
                          className={cx(
                            'h-1.5 w-1.5 rounded-full',
                            task.workflow === 'LEAVE_APPROVAL' ? 'bg-brand-600' : 'bg-info-500',
                          )}
                        />
                        <span className="text-[12.5px]">{WORKFLOW_LABEL[task.workflow]}</span>
                      </span>
                      <span className="mt-0.5 block text-[11px] text-ink-400 tnum">
                        {task.duration_label}
                      </span>
                    </Td>
                    <Td>
                      <span className="block text-[12px] text-ink-700">
                        {task.detail_line}
                      </span>
                      <span className="block text-[11px] text-ink-400">
                        {task.submitted_at ? relativeTime(task.submitted_at) : 'not yet run'}
                      </span>
                    </Td>
                    <Td>
                      <ProvenanceBadge provenance={rec.provenance} />
                    </Td>
                    <Td>
                      <StageBadge stage={task.stage} />
                    </Td>
                    <Td className="text-right">
                      {/* The wrapper stops the row's navigate handler from firing. */}
                      <span onClick={(e) => e.stopPropagation()}>
                      <Button
                        size="sm"
                        variant={task.job_id ? 'ghost' : 'dark'}
                        icon={<Play size={12} />}
                        disabled={running !== null}
                        onClick={() => void runTask(task)}
                      >
                        {running === rec.record_id
                          ? 'Running…'
                          : task.job_id
                            ? 'Re-run'
                            : 'Run agent'}
                      </Button>
                      </span>
                    </Td>
                  </tr>
                )
              })}
            </tbody>
          </Table>
        )}

        {!loading && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3">
            <p className="text-[12px] text-ink-400">
              Showing <span className="tnum font-semibold text-ink-700">{filtered.length}</span> of{' '}
              <span className="tnum">{tasks.length}</span> tasks
            </p>
            <div className="flex items-center gap-1">
              <Button size="sm" variant="ghost" disabled>
                Previous
              </Button>
              <span className="rounded-md bg-ink-900 px-2.5 py-1 text-[11.5px] font-semibold text-white">
                1
              </span>
              <Button size="sm" variant="ghost" disabled>
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>

      <div className="mt-5 grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader
            title="Queue dispatch"
            subtitle="Records are processed one at a time, in order."
            action={<Badge tone="ok" dot>Ready</Badge>}
          />
          <p className="mt-3 text-[12px] leading-snug text-ink-500">
            The orchestrator pulls one pending record, runs it through the state machine, and does
            not begin the next until the current job reaches a terminal state.
          </p>
        </Card>
        <Card>
          <CardHeader
            title="Escalation policy"
            subtitle="require_human_review_if_missing_data"
            action={<Badge tone="warn">Active</Badge>}
          />
          <p className="mt-3 text-[12px] leading-snug text-ink-500">
            Incomplete records escalate rather than fail. Auto-rejection is disabled entirely —
            the 差戻し control was never observed being used in Dataset B.
          </p>
        </Card>
        <Card>
          <CardHeader title="Target system" subtitle="HR人事給与システム" action={<Badge tone="neutral">Planned</Badge>} />
          <p className="mt-3 font-mono text-[11.5px] leading-snug text-ink-500">
            127.0.0.1:5132/#/leave-applications
          </p>
          <p className="mt-2 text-[12px] leading-snug text-ink-500">
            Playwright will drive this surface once the executor stage is built.
          </p>
        </Card>
      </div>
    </>
  )
}
