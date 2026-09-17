import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRightLeft,
  Check,
  ChevronRight,
  Clock,
  FileSearch,
  Scale,
  ShieldQuestion,
  UserCheck,
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
  cx,
} from '@/components/ui'
import {
  AmbiguityCallout,
  ConfidenceMeter,
  FieldRow,
  PolicyGateCard,
  ProvenanceBadge,
  Timeline,
} from '@/components/domain'
import { useAsync } from '@/hooks/useAsync'
import { fetchJob, fetchJobs, submitHumanDecision } from '@/services/api'
import { STATE_LABEL, clockTime, relativeTime } from '@/lib/format'
import type { LeaveRequest } from '@/types'

function ReviewQueue() {
  const navigate = useNavigate()
  const { data, loading, error, reload } = useAsync(fetchJobs, [])

  if (error) return <ErrorState message={error} onRetry={reload} />
  if (loading || !data) return <LoadingState label="Loading review queue…" />

  const queue = data.filter((j) => j.state === 'HUMAN_REVIEW')

  return (
    <>
      <PageHeader
        title="Human Review Queue"
        badge={<Badge tone="warn" dot>{queue.length} awaiting</Badge>}
        subtitle="Records the policy could not decide. The platform will not act on any of these until a person does."
      />
      {queue.length === 0 ? (
        <Card>
          <EmptyState
            title="Review queue is clear"
            detail="Every job was resolved by the policy engine."
            icon={<UserCheck size={22} />}
          />
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {queue.map((job) => {
            const rec = job.record as LeaveRequest
            return (
              <Card key={job.job_id} className="flex flex-col">
                <div className="flex items-start gap-3">
                  <Avatar name={rec.employee_name} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[13.5px] font-bold text-ink-900">
                      {rec.employee_name ?? rec.record_id}
                    </p>
                    <Mono className="text-[11px] text-ink-400">{rec.record_id}</Mono>
                  </div>
                  <Badge tone="warn">{relativeTime(job.updated_at)}</Badge>
                </div>

                <div className="mt-3">
                  <Badge tone="warn" dot>
                    {job.decision?.ambiguity_type?.replace(/_/g, ' ').toLowerCase()}
                  </Badge>
                </div>

                <p className="mt-2.5 line-clamp-3 flex-1 text-[12px] leading-snug text-ink-500">
                  {job.decision?.reason}
                </p>

                <div className="mt-3 flex items-center justify-between border-t border-line pt-3">
                  <span className="text-[11.5px] text-ink-400">
                    {rec.request_type ?? '—'} · {rec.request_date ?? 'no date'}
                  </span>
                  <Button size="sm" variant="dark" onClick={() => navigate(`/review/${job.job_id}`)}>
                    Review
                  </Button>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </>
  )
}

export default function HumanReview() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const { data: job, loading, error, reload } = useAsync(
    () => (jobId ? fetchJob(jobId) : Promise.resolve(null)),
    [jobId],
  )

  const [choice, setChoice] = useState<'APPROVE' | 'REJECT' | 'RESUBMIT' | null>(null)
  const [note, setNote] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  if (!jobId) return <ReviewQueue />
  if (error) return <ErrorState message={error} onRetry={reload} />
  if (loading || !job) return <LoadingState label="Loading review…" />

  const rec = job.record as LeaveRequest
  const decision = job.decision
  const gates = decision?.policy_checks ?? []
  const blocking = gates.filter((g) => g.passed !== true)

  /**
   * Record the determination and carry it out. This is the only path by which a
   * rejection ever reaches the browser: the policy layer is not permitted to
   * perform one unattended. The run happens server-side while this awaits, so a
   * failure here is a real execution or verification failure and is shown as one.
   */
  async function confirm() {
    if (!choice || choice === 'RESUBMIT') return
    setSubmitting(true)
    setSubmitError(null)
    try {
      await submitHumanDecision(job!.job_id, choice, note, 'operator')
      await reload()
      setSubmitted(true)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <nav className="mb-3 flex items-center gap-1.5 text-[12.5px] text-ink-400">
        <button onClick={() => navigate('/review')} className="hover:text-ink-900">
          Human review
        </button>
        <ChevronRight size={12} />
        <Mono className="font-semibold text-brand-600">{job.job_id}</Mono>
      </nav>

      {decision && (
        <div className="mb-5">
          <AmbiguityCallout reason={decision.reason} ambiguity={decision.ambiguity_type} />
        </div>
      )}

      <PageHeader
        title={`Review: ${rec.employee_name ?? rec.record_id}`}
        badge={<Badge tone="warn" dot pulse>Awaiting operator determination</Badge>}
        meta={
          <>
            <span>{job.job_id}</span>
            <span>·</span>
            <span>{rec.request_type ?? '—'}</span>
            <span>·</span>
            <span>Escalated {relativeTime(job.updated_at)}</span>
          </>
        }
        actions={
          <>
            <Button variant="secondary" icon={<FileSearch size={14} />}>
              Employee record
            </Button>
            <Button
              variant="secondary"
              icon={<ArrowRightLeft size={14} />}
              onClick={() => navigate(`/agent/${job.job_id}`)}
            >
              Agent evaluation
            </Button>
          </>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-5">
          <Card>
            <CardHeader
              title="Why this stopped"
              subtitle="Gates that did not clear. Everything else passed."
              icon={<ShieldQuestion size={16} />}
              action={
                <Badge tone="warn">{blocking.length} of {gates.length} unresolved</Badge>
              }
            />
            <div className="mt-4 space-y-2.5">
              {gates.map((check, i) => (
                <PolicyGateCard key={check.check_id} check={check} index={i} />
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Record under review"
              subtitle="Exactly the fields the policy evaluated"
              icon={<FileSearch size={16} />}
              action={<ProvenanceBadge provenance={rec.provenance} />}
            />
            <div className="mt-4 grid gap-5 sm:grid-cols-2">
              <div className="flex items-start gap-3">
                <Avatar name={rec.employee_name} size="lg" />
                <div>
                  <p className="text-[14px] font-bold text-ink-900">{rec.employee_name ?? '—'}</p>
                  <Mono className="text-[11.5px] text-ink-400">
                    {rec.employee_id ?? 'no employee_id'}
                  </Mono>
                  <p className="mt-0.5 text-[12px] text-ink-500">
                    {rec.department ?? 'department missing'}
                  </p>
                </div>
              </div>
              <dl>
                <FieldRow label="管理ID" value={rec.record_id} mono />
                <FieldRow label="申請種別" value={rec.request_type ?? ''} missing={!rec.request_type} />
                <FieldRow label="期間" value={rec.request_date ?? ''} mono missing={!rec.request_date} />
                <FieldRow label="ステータス" value={rec.status} />
              </dl>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div
                className={cx(
                  'rounded-lg border p-3.5',
                  rec.prior_approval_required === null
                    ? 'border-warn-100 bg-warn-50'
                    : 'border-line bg-surface-sunken',
                )}
              >
                <p className="label-xs text-ink-400">事前承認要否 (required)</p>
                <p className="mt-1 text-[14px] font-bold text-ink-900">
                  {rec.prior_approval_required === null
                    ? 'Unknown'
                    : rec.prior_approval_required
                      ? '要 — required'
                      : '不要 — not required'}
                </p>
                <p className="mt-1 text-[11px] leading-snug text-ink-500">
                  {rec.prior_approval_required === null
                    ? 'Detail panel was never opened for this record in Dataset B.'
                    : 'Read from the record detail panel.'}
                </p>
              </div>
              <div
                className={cx(
                  'rounded-lg border p-3.5',
                  rec.prior_approval_obtained === null
                    ? 'border-warn-100 bg-warn-50'
                    : 'border-line bg-surface-sunken',
                )}
              >
                <p className="label-xs text-ink-400">Prior approval obtained</p>
                <p className="mt-1 text-[14px] font-bold text-ink-900">
                  {rec.prior_approval_obtained === null
                    ? 'Unknown'
                    : rec.prior_approval_obtained
                      ? 'Yes'
                      : 'No'}
                </p>
                <p className="mt-1 text-[11px] leading-snug text-ink-500">
                  Prototype-only field — Dataset B showed whether approval was <em>required</em>,
                  never whether it was <em>obtained</em>.
                </p>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Escalation trail" icon={<Clock size={16} />} />
            <div className="mt-4">
              <Timeline
                items={job.state_history.map((t) => ({
                  title: `${STATE_LABEL[t.from_state]} → ${STATE_LABEL[t.to_state]}`,
                  detail: t.note,
                  time: clockTime(t.at),
                  tone: t.to_state === 'HUMAN_REVIEW' ? 'warn' : 'brand',
                  active: t.to_state === 'HUMAN_REVIEW',
                }))}
              />
            </div>
          </Card>
        </div>

        {/* Operator panel */}
        <div className="space-y-5">
          <Card>
            <CardHeader
              title="Agent recommendation"
              subtitle="What the policy engine concluded, and how sure it was"
              icon={<Scale size={16} />}
            />
            {decision && (
              <div className="mt-4 space-y-4">
                <blockquote className="rounded-lg border-l-2 border-warn-500 bg-warn-50 p-3 text-[12.5px] leading-snug text-warn-700">
                  {decision.reason}
                </blockquote>
                <ConfidenceMeter value={decision.confidence} />
                <p className="rounded-lg bg-surface-sunken p-3 text-[11.5px] leading-snug text-ink-500">
                  The agent did not choose an outcome here. It reported that the explicit policy does
                  not resolve this case — deciding it is the operator's call.
                </p>
              </div>
            )}
          </Card>

          <Card className={cx(submitted && 'border-ok-100 bg-ok-50')}>
            <CardHeader
              title="Operator determination"
              subtitle={submitted ? undefined : 'Required before this job can move'}
              icon={<UserCheck size={16} />}
              action={
                submitted ? (
                  <Badge tone="ok" dot>Recorded</Badge>
                ) : (
                  <Badge tone="warn">Mandatory</Badge>
                )
              }
            />

            {submitted ? (
              <div className="mt-4 space-y-3">
                <p className="text-[13px] font-semibold text-ok-700">
                  Determination recorded and carried out: {choice}
                </p>
                <p className="text-[12px] leading-snug text-ok-700/90">
                  Your authorisation released the action to the executor, which performed it in the
                  HR system and then independently re-read the record. Job is now{' '}
                  <span className="font-mono">{job.state}</span>
                  {job.execution ? (
                    <>
                      {' '}— verification{' '}
                      <span className="font-mono">{job.execution.verification_status}</span>,{' '}
                      {job.execution.status_before} → {job.execution.status_after}.
                    </>
                  ) : (
                    '.'
                  )}
                </p>
                <p className="text-[12px] leading-snug text-ok-700/90">
                  There is no undo: the record has actually changed in the target system. Your note
                  is written into the HR system's comment field alongside the action.
                </p>
                <Button variant="secondary" onClick={() => navigate(`/execution/${job.job_id}`)}>
                  View execution trace
                </Button>
              </div>
            ) : submitError ? (
              <div className="mt-4 space-y-3">
                <p className="text-[13px] font-semibold text-risk-700">Execution failed</p>
                <p className="text-[12px] leading-snug text-risk-700/90">{submitError}</p>
                <Button variant="secondary" onClick={() => setSubmitError(null)}>
                  Back to the form
                </Button>
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                <div className="space-y-2">
                  {[
                    {
                      id: 'APPROVE' as const,
                      label: 'Approve with justification',
                      detail: 'Authorise the request despite the unresolved gate.',
                      tone: 'ok' as const,
                    },
                    {
                      id: 'RESUBMIT' as const,
                      label: 'Request more information',
                      detail: 'Send back for the missing prior-approval evidence.',
                      tone: 'warn' as const,
                    },
                    {
                      id: 'REJECT' as const,
                      label: 'Reject request',
                      detail: 'Return the request (差戻し). Never performed automatically.',
                      tone: 'risk' as const,
                    },
                  ].map((opt) => (
                    <label
                      key={opt.id}
                      className={cx(
                        'flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors',
                        choice === opt.id
                          ? 'border-brand-400 bg-brand-50'
                          : 'border-line bg-surface hover:bg-surface-sunken',
                      )}
                    >
                      <input
                        type="radio"
                        name="determination"
                        checked={choice === opt.id}
                        onChange={() => setChoice(opt.id)}
                        className="mt-0.5 h-3.5 w-3.5 accent-brand-600"
                      />
                      <span>
                        <span className="block text-[12.5px] font-semibold text-ink-900">
                          {opt.label}
                        </span>
                        <span className="block text-[11.5px] leading-snug text-ink-500">
                          {opt.detail}
                        </span>
                      </span>
                    </label>
                  ))}
                </div>

                <div>
                  <label
                    htmlFor="review-note"
                    className="label-xs mb-1.5 block text-ink-400"
                  >
                    Audit note
                  </label>
                  <textarea
                    id="review-note"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    rows={4}
                    placeholder="Record the justification. This is written to the job's audit trail."
                    className="w-full rounded-lg border border-line bg-surface p-3 text-[12.5px] placeholder:text-ink-300 focus:border-brand-400 focus:outline-none"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="dark"
                    icon={<Check size={14} />}
                    disabled={!choice || !note.trim() || submitting}
                    onClick={confirm}
                    className="flex-1"
                    title={!choice ? 'Select a determination' : !note.trim() ? 'An audit note is required' : undefined}
                  >
                    {submitting ? 'Recording…' : 'Confirm decision'}
                  </Button>
                  <Button
                    variant="ghost"
                    icon={<X size={14} />}
                    onClick={() => { setChoice(null); setNote('') }}
                  >
                    Reset
                  </Button>
                </div>
              </div>
            )}
          </Card>

          <Card className="border-warn-100">
            <div className="flex items-start gap-2.5">
              <AlertTriangle size={15} className="mt-0.5 shrink-0 text-warn-700" />
              <p className="text-[11.5px] leading-snug text-ink-500">
                <strong className="font-semibold text-ink-700">Reject is never automatic.</strong>{' '}
                The 差戻し control exists in the HR system but was never observed being used in any
                inspected Dataset B segment, so the prototype has no evidence of what rejection
                requires. Only a human can take that path.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
