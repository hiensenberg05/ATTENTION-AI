import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowRight,
  Check,
  ChevronRight,
  CircleDashed,
  Loader2,
  MonitorPlay,
  MousePointerClick,
  RotateCcw,
  ShieldCheck,
  X,
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
  LoadingState,
  Mono,
  Table,
  Td,
  Th,
  cx,
} from '@/components/ui'
import { DecisionBadge, FieldRow, StateBadge, Timeline } from '@/components/domain'
import { useAsync } from '@/hooks/useAsync'
import { fetchJob, fetchJobs, fetchWorkflow } from '@/services/api'
import { recordSubtitle, WORKFLOW_LABEL } from '@/lib/record'

import { STATE_LABEL, clockTime, relativeTime, seconds } from '@/lib/format'

function ExecutionPicker() {
  const navigate = useNavigate()
  const { data, loading, error, reload } = useAsync(fetchJobs, [])

  if (error) return <ErrorState message={error} onRetry={reload} />
  if (loading || !data) return <LoadingState label="Loading executions…" />

  const executable = data.filter(
    (j) => j.execution || j.state === 'EXECUTING' || j.state === 'POLICY_CHECK',
  )

  return (
    <>
      <PageHeader
        title="Step Automation Execution"
        subtitle="Deterministic browser actions. By the time a job reaches this screen the decision is already made — execution performs it and independently verifies the result."
      />
      <Card padded={false}>
        {executable.length === 0 ? (
          <EmptyState title="Nothing to execute" detail="Jobs appear here once a decision routes them to execution." />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Job</Th>
                <Th>Subject</Th>
                <Th>Decision</Th>
                <Th>State</Th>
                <Th>Verification</Th>
                <Th align="right">Duration</Th>
              </tr>
            </thead>
            <tbody>
              {executable.map((job) => {
                const rec = job.record
                return (
                  <tr
                    key={job.job_id}
                    onClick={() => navigate(`/execution/${job.job_id}`)}
                    className="cursor-pointer transition-colors hover:bg-surface-sunken"
                  >
                    <Td><Mono className="font-semibold text-brand-600">{job.job_id}</Mono></Td>
                    <Td>
                      <span className="flex items-center gap-2.5">
                        <Avatar name={rec.employee_name} size="sm" />
                        <span className="font-semibold text-ink-900">{rec.employee_name ?? '—'}</span>
                      </span>
                    </Td>
                    <Td>
                      {job.decision ? <DecisionBadge decision={job.decision.decision} /> : '—'}
                    </Td>
                    <Td><StateBadge state={job.state} pulse={job.state === 'EXECUTING'} /></Td>
                    <Td>
                      <Badge
                        tone={
                          job.execution?.verification_status === 'VERIFIED'
                            ? 'ok'
                            : job.execution?.verification_status === 'FAILED'
                              ? 'risk'
                              : 'neutral'
                        }
                      >
                        {job.execution?.verification_status ?? 'NOT_ATTEMPTED'}
                      </Badge>
                    </Td>
                    <Td align="right">
                      <Mono className="text-ink-500">{seconds(job.execution?.duration_seconds)}</Mono>
                    </Td>
                  </tr>
                )
              })}
            </tbody>
          </Table>
        )}
      </Card>
    </>
  )
}

export default function Execution() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const { data: job, loading, error, reload } = useAsync(
    () => (jobId ? fetchJob(jobId) : Promise.resolve(null)),
    [jobId],
  )

  // The workflow's own Phase 2 evidence, so a payroll run never cites the leave
  // segment. Loaded lazily; the copy degrades gracefully while it is in flight.
  const { data: definition } = useAsync(
    () => (job ? fetchWorkflow(job.workflow) : Promise.resolve(null)),
    [job?.workflow],
  )
  const evidenceSegment = definition?.evidence.clean_instance_segment_id ?? null

  /** Optional replay of the recorded steps, for inspecting a finished run. */
  const [simStep, setSimStep] = useState<number | null>(null)

  useEffect(() => {
    if (simStep === null) return
    const steps = job?.execution?.steps_completed.length ?? 7
    if (simStep >= steps) return
    const t = setTimeout(() => setSimStep((s) => (s === null ? null : s + 1)), 620)
    return () => clearTimeout(t)
  }, [simStep, job])

  if (!jobId) return <ExecutionPicker />
  if (error) return <ErrorState message={error} onRetry={reload} />
  if (loading || !job) return <LoadingState label="Loading execution…" />

  const rec = job.record
  const exec = job.execution
  const decision = job.decision

  // No fallback list: a job with no execution has not performed any steps, and
  // inventing a plausible-looking sequence would be indistinguishable from a real
  // one on screen. An empty list renders the empty state instead.
  const stepNames = exec?.steps_completed.map((s) => s.name) ?? []

  const completedCount =
    simStep !== null
      ? Math.min(simStep, stepNames.length)
      : (exec?.steps_completed.filter((s) => s.completed).length ?? 0)

  const running = simStep !== null && simStep < stepNames.length
  const verified = exec?.verification_status === 'VERIFIED'
  const failed = exec?.verification_status === 'FAILED'

  return (
    <>
      <nav className="mb-3 flex items-center gap-1.5 text-[12.5px] text-ink-400">
        <button onClick={() => navigate('/queue')} className="hover:text-ink-900">Queue</button>
        <ChevronRight size={12} />
        <button onClick={() => navigate(`/agent/${job.job_id}`)} className="hover:text-ink-900">
          Agent decision
        </button>
        <ChevronRight size={12} />
        <Mono className="font-semibold text-brand-600">Execution</Mono>
      </nav>

      <PageHeader
        title={`Execution: ${rec.employee_name ?? rec.record_id}`}
        badge={
          failed ? (
            <Badge tone="risk" dot>Verification failed</Badge>
          ) : verified ? (
            <Badge tone="ok" dot>Verified</Badge>
          ) : running ? (
            <Badge tone="info" dot pulse>Running</Badge>
          ) : (
            <Badge tone="neutral" dot>Ready</Badge>
          )
        }
        subtitle="Playwright performs the decided action, then re-reads the record. Clicking successfully is not the same as the record being approved — those are tracked separately."
        meta={
          <>
            <span>{job.job_id}</span>
            <span>·</span>
            <span>Action {exec?.action ?? 'APPROVE_LEAVE'}</span>
            <span>·</span>
            <span>Target Mock HR: same FastAPI service</span>
          </>
        }
        actions={
          <>
            <Button
              variant="secondary"
              icon={<RotateCcw size={14} />}
              onClick={() => setSimStep(0)}
              disabled={running}
            >
              Replay steps
            </Button>
            <Button
              variant="dark"
              icon={running ? <Loader2 size={14} className="animate-spin" /> : <MonitorPlay size={14} />}
              onClick={() => setSimStep(0)}
              disabled={running}
            >
              {running ? 'Executing…' : 'Simulate execution'}
            </Button>
          </>
        }
      />

      <div className="mb-5 rounded-lg border border-line bg-surface px-4 py-3">
        <p className="text-[12px] leading-snug text-ink-500">
          <strong className="font-semibold text-ink-700">Real run.</strong> These steps were
          performed by Playwright against the mock HR system, locating every control by{' '}
          <span className="font-mono">data-testid</span> — never by coordinates. The sequence
          mirrors the human one confirmed by screenshot in Dataset B
          {evidenceSegment ? (
            <>
              {' '}segment <span className="font-mono">{evidenceSegment}</span>
            </>
          ) : (
            ' for this workflow'
          )}
          .
        </p>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-5">
          <Card>
            <CardHeader
              title="Deterministic steps"
              subtitle="Fixed sequence. No judgement is made at this stage."
              icon={<MousePointerClick size={16} />}
              action={
                <Badge tone={completedCount === stepNames.length ? 'ok' : 'info'}>
                  {completedCount}/{stepNames.length}
                </Badge>
              }
            />
            <ol className="mt-4 space-y-2">
              {stepNames.map((name, i) => {
                const done = i < completedCount
                const active = running && i === completedCount
                const stepDetail = exec?.steps_completed[i]?.detail
                return (
                  <li
                    key={name}
                    className={cx(
                      'flex items-start gap-3 rounded-lg border p-3 transition-colors',
                      done
                        ? 'border-ok-100 bg-ok-50'
                        : active
                          ? 'border-info-100 bg-info-50'
                          : 'border-line bg-surface-sunken',
                    )}
                  >
                    <span
                      className={cx(
                        'mt-px inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-white',
                        done ? 'bg-ok-500' : active ? 'bg-info-500' : 'bg-ink-300',
                      )}
                    >
                      {done ? (
                        <Check size={12} strokeWidth={3} />
                      ) : active ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <CircleDashed size={12} />
                      )}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-[12.5px] font-semibold text-ink-900">
                        <span className="font-mono text-[11px] text-ink-400">
                          {String(i + 1).padStart(2, '0')}
                        </span>{' '}
                        {name}
                      </p>
                      {done && stepDetail && (
                        <p className="mt-0.5 text-[11.5px] text-ink-500">{stepDetail}</p>
                      )}
                    </div>
                    {done && exec?.steps_completed[i]?.at && (
                      <Mono className="shrink-0 text-[10.5px] text-ink-400">
                        {clockTime(exec.steps_completed[i].at!)}
                      </Mono>
                    )}
                  </li>
                )
              })}
            </ol>
          </Card>

          <Card>
            <CardHeader
              title="Verification"
              subtitle="Did the record's real status actually change?"
              icon={<ShieldCheck size={16} />}
            />
            <div className="mt-4 flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-3 rounded-lg border border-line bg-surface-sunken px-4 py-3">
                <div className="text-center">
                  <p className="label-xs text-ink-400">Before</p>
                  <p className="mt-1 text-[15px] font-bold text-ink-900">
                    {exec?.status_before ?? '申請中'}
                  </p>
                </div>
                <ArrowRight size={16} className="text-ink-300" />
                <div className="text-center">
                  <p className="label-xs text-ink-400">After</p>
                  <p
                    className={cx(
                      'mt-1 text-[15px] font-bold',
                      verified ? 'text-ok-700' : failed ? 'text-risk-700' : 'text-ink-300',
                    )}
                  >
                    {completedCount === stepNames.length ? (exec?.status_after ?? '承認済み') : '—'}
                  </p>
                </div>
              </div>

              <div
                className={cx(
                  'flex items-center gap-2.5 rounded-lg border px-4 py-3',
                  verified
                    ? 'border-ok-100 bg-ok-50 text-ok-700'
                    : failed
                      ? 'border-risk-100 bg-risk-50 text-risk-700'
                      : 'border-line bg-surface-sunken text-ink-500',
                )}
              >
                {verified ? <Check size={16} /> : failed ? <X size={16} /> : <CircleDashed size={16} />}
                <div>
                  <p className="text-[12.5px] font-bold">
                    {exec?.verification_status ?? 'NOT_ATTEMPTED'}
                  </p>
                  <p className="text-[11.5px] opacity-80">
                    {verified
                      ? 'Status re-read and confirmed changed'
                      : failed
                        ? exec?.error ?? 'Status did not change'
                        : 'Awaiting execution'}
                  </p>
                </div>
              </div>
            </div>

            <p className="mt-4 rounded-lg bg-surface-sunken p-3 text-[11.5px] leading-snug text-ink-500">
              <strong className="font-semibold text-ink-700">Caveat.</strong> The post-action label{' '}
              <span className="font-mono">承認済み</span> is a prototype assumption — no approved
              record was ever captured in Dataset B, so the expected status must be confirmed
              against the real system before this verification means anything.
            </p>
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader title="Job context" />
            <div className="mt-3 flex items-center gap-3">
              <Avatar name={rec.employee_name} />
              <div>
                <p className="text-[13px] font-bold text-ink-900">{rec.employee_name ?? '—'}</p>
                <Mono className="text-[11px] text-ink-400">{rec.record_id}</Mono>
              </div>
            </div>
            <dl className="mt-3">
              <FieldRow label="Workflow" value={WORKFLOW_LABEL[job.workflow]} />
              <FieldRow label="Record" value={recordSubtitle(rec)} />
              <FieldRow label="Decision" value={decision?.decision ?? '—'} mono />
              <FieldRow label="Executed by" value={exec?.executed_by ?? 'agent'} />
              <FieldRow label="Duration" value={seconds(exec?.duration_seconds)} mono />
            </dl>
          </Card>

          <Card>
            <CardHeader title="State transitions" />
            <div className="mt-4">
              <Timeline
                items={job.state_history.map((t) => ({
                  title: `${STATE_LABEL[t.from_state]} → ${STATE_LABEL[t.to_state]}`,
                  detail: t.note,
                  time: clockTime(t.at),
                  tone: t.to_state === 'FAILED' ? 'risk' : t.to_state === 'COMPLETED' ? 'ok' : 'brand',
                }))}
              />
            </div>
          </Card>

          <Card className="bg-rail-900 text-rail-200">
            <h3 className="text-[12.5px] font-bold text-white">Execution log</h3>
            <div className="mt-2.5 space-y-1 font-mono text-[10.5px] leading-relaxed">
              {stepNames.slice(0, completedCount).map((name, i) => (
                <p key={name} className="text-rail-300">
                  <span className="text-ok-500">✓</span>{' '}
                  <span className="text-rail-400">
                    {exec?.steps_completed[i]?.at ? clockTime(exec.steps_completed[i].at!) : '--:--:--'}
                  </span>{' '}
                  {name}
                </p>
              ))}
              {running && (
                <p className="text-brand-400">
                  <span className="animate-pulse-dot">▸</span> {stepNames[completedCount]}…
                </p>
              )}
              {completedCount === 0 && !running && (
                <p className="text-rail-400">Awaiting execution…</p>
              )}
            </div>
            <p className="mt-3 border-t border-rail-700 pt-2.5 text-[10px] text-rail-400">
              Updated {relativeTime(job.updated_at)}
            </p>
          </Card>
        </div>
      </div>
    </>
  )
}
