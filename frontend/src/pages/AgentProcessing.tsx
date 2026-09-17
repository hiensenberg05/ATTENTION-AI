import { useNavigate, useParams } from 'react-router-dom'
import {
  ChevronRight,
  Cpu,
  FileSearch,
  Flag,
  PlayCircle,
  ScrollText,
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
import {
  AmbiguityCallout,
  ConfidenceMeter,
  DecisionBadge,
  FieldRow,
  PolicyGateCard,
  ProvenanceBadge,
  StateBadge,
  Timeline,
} from '@/components/domain'
import { useAsync } from '@/hooks/useAsync'
import { fetchJob, fetchJobs } from '@/services/api'
import { STATE_LABEL, clockTime, relativeTime } from '@/lib/format'
import type { LeaveRequest } from '@/types'

/** Picker shown at /agent when no specific job is selected. */
function JobPicker() {
  const navigate = useNavigate()
  const { data, loading, error, reload } = useAsync(fetchJobs, [])

  if (error) return <ErrorState message={error} onRetry={reload} />
  if (loading || !data) return <LoadingState label="Loading jobs…" />

  const decided = data.filter((j) => j.decision)

  return (
    <>
      <PageHeader
        title="Agent Policy & Decision"
        subtitle="Select a job to inspect how the policy engine evaluated it — which gates cleared, what it decided, and why."
      />
      <Card padded={false}>
        {decided.length === 0 ? (
          <EmptyState title="No decided jobs yet" detail="Jobs appear here once they reach the policy-check stage." />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Job</Th>
                <Th>Subject</Th>
                <Th>Request</Th>
                <Th>Decision</Th>
                <Th>State</Th>
                <Th align="right">Updated</Th>
              </tr>
            </thead>
            <tbody>
              {decided.map((job) => {
                const rec = job.record as LeaveRequest
                return (
                  <tr
                    key={job.job_id}
                    onClick={() => navigate(`/agent/${job.job_id}`)}
                    className="cursor-pointer transition-colors hover:bg-surface-sunken"
                  >
                    <Td>
                      <Mono className="font-semibold text-brand-600">{job.job_id}</Mono>
                    </Td>
                    <Td>
                      <span className="flex items-center gap-2.5">
                        <Avatar name={rec.employee_name} size="sm" />
                        <span>
                          <span className="block font-semibold text-ink-900">
                            {rec.employee_name ?? '—'}
                          </span>
                          <Mono className="text-[10.5px] text-ink-400">{rec.record_id}</Mono>
                        </span>
                      </span>
                    </Td>
                    <Td>{rec.request_type ?? '—'}</Td>
                    <Td>
                      <DecisionBadge
                        decision={job.decision!.decision}
                        confidence={job.decision!.confidence}
                      />
                    </Td>
                    <Td>
                      <StateBadge state={job.state} />
                    </Td>
                    <Td align="right">
                      <Mono className="text-ink-400">{relativeTime(job.updated_at)}</Mono>
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

export default function AgentProcessing() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const { data: job, loading, error, reload } = useAsync(
    () => (jobId ? fetchJob(jobId) : Promise.resolve(null)),
    [jobId],
  )

  if (!jobId) return <JobPicker />
  if (error) return <ErrorState message={error} onRetry={reload} />
  if (loading || !job) return <LoadingState label="Loading agent evaluation…" />

  const rec = job.record as LeaveRequest
  const decision = job.decision
  const gates = decision?.policy_checks ?? []
  const cleared = gates.filter((g) => g.passed === true).length
  const isApprove = decision?.decision === 'APPROVE'

  return (
    <>
      <nav className="mb-3 flex items-center gap-1.5 text-[12.5px] text-ink-400">
        <button onClick={() => navigate('/queue')} className="hover:text-ink-900">
          Queue
        </button>
        <ChevronRight size={12} />
        <button onClick={() => navigate('/agent')} className="hover:text-ink-900">
          Leave Approval
        </button>
        <ChevronRight size={12} />
        <Mono className="font-semibold text-brand-600">{job.job_id}</Mono>
      </nav>

      <PageHeader
        title={`Policy evaluation: ${rec.employee_name ?? rec.record_id}`}
        badge={
          decision ? (
            <Badge tone={isApprove ? 'ok' : 'warn'} dot>
              {isApprove
                ? `Recommended for auto-approval (${(decision.confidence * 100).toFixed(1)}%)`
                : `Escalated to human review (${(decision.confidence * 100).toFixed(1)}%)`}
            </Badge>
          ) : undefined
        }
        meta={
          <>
            <span>{cleared} of {gates.length} policy gates cleared</span>
            <span>·</span>
            <span>Record {rec.record_id}</span>
            <span>·</span>
            <span>Policy {decision?.policy_version}</span>
          </>
        }
        actions={
          <>
            {isApprove && (
              <Button
                variant="dark"
                icon={<PlayCircle size={14} />}
                onClick={() => navigate(`/execution/${job.job_id}`)}
              >
                Execute approval
              </Button>
            )}
            <Button
              variant="secondary"
              icon={<Flag size={14} />}
              onClick={() => navigate(`/review/${job.job_id}`)}
            >
              Flag for human review
            </Button>
            <Button variant="danger" icon={<X size={14} />} title="Auto-rejection is disabled by policy" disabled>
              Override &amp; reject
            </Button>
          </>
        }
      />

      {decision && !isApprove && (
        <div className="mb-5">
          <AmbiguityCallout reason={decision.reason} ambiguity={decision.ambiguity_type} />
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[340px_minmax(0,1fr)_320px]">
        {/* Left — the record */}
        <div className="space-y-5">
          <Card>
            <CardHeader title="Submitted record" icon={<FileSearch size={16} />} />
            <div className="mt-4 flex items-center gap-3">
              <Avatar name={rec.employee_name} size="lg" />
              <div className="min-w-0">
                <p className="text-[15px] font-bold text-ink-900">{rec.employee_name ?? '—'}</p>
                <Mono className="text-[11.5px] text-ink-400">{rec.employee_id ?? 'no employee_id'}</Mono>
                <p className="mt-0.5 text-[12px] text-ink-500">{rec.department ?? 'department missing'}</p>
              </div>
            </div>

            <div className="mt-4">
              <ProvenanceBadge provenance={rec.provenance} />
            </div>

            <dl className="mt-4">
              <FieldRow label="管理ID / Record" value={rec.record_id} mono />
              <FieldRow label="申請種別 / Type" value={rec.request_type ?? ''} missing={!rec.request_type} />
              <FieldRow label="期間 / Date" value={rec.request_date ?? ''} mono missing={!rec.request_date} />
              <FieldRow label="所属部署 / Dept" value={rec.department ?? ''} missing={!rec.department} />
              <FieldRow label="ステータス / Status" value={rec.status} />
              <FieldRow
                label="事前承認要否"
                value={
                  rec.prior_approval_required === null
                    ? <span className="text-warn-700">unknown</span>
                    : rec.prior_approval_required ? '要 (required)' : '不要 (not required)'
                }
              />
              <FieldRow
                label="Prior approval obtained"
                value={
                  rec.prior_approval_obtained === null
                    ? <span className="text-warn-700">unknown</span>
                    : rec.prior_approval_obtained ? 'yes' : 'no'
                }
              />
            </dl>

            {rec.comment && (
              <blockquote className="mt-3 rounded-lg border-l-2 border-brand-400 bg-surface-sunken p-3 text-[12px] italic text-ink-500">
                {rec.comment}
              </blockquote>
            )}
          </Card>

          {rec.evidence_note && (
            <Card className="border-ok-100 bg-ok-50">
              <CardHeader title="Dataset B evidence" icon={<ShieldCheck size={16} />} />
              <p className="mt-2.5 text-[12px] leading-snug text-ok-700">{rec.evidence_note}</p>
            </Card>
          )}
        </div>

        {/* Middle — the gates */}
        <div className="space-y-5">
          <Card>
            <CardHeader
              title="Policy engine verification"
              subtitle="Each gate is an explicit rule from policies.json, evaluated against this record."
              icon={<ShieldCheck size={16} />}
              action={
                <Badge tone={cleared === gates.length ? 'ok' : 'warn'}>
                  {cleared}/{gates.length} cleared
                </Badge>
              }
            />
            <div className="mt-4 space-y-2.5">
              {gates.map((check, i) => (
                <PolicyGateCard key={check.check_id} check={check} index={i} />
              ))}
            </div>
            <p className="mt-4 rounded-lg bg-surface-sunken p-3 text-[11.5px] leading-snug text-ink-500">
              <strong className="font-semibold text-ink-700">Note.</strong> These rules are an
              explicit prototype policy, hand-authored in{' '}
              <span className="font-mono">policies.json</span>. Dataset B's logs showed only that an
              operator acted — never the rule that justified it. Nothing here was learned from the
              logs.
            </p>
          </Card>

          <Card>
            <CardHeader title="Pipeline transitions" subtitle="State ≠ decision — both are tracked" />
            <div className="mt-4">
              <Timeline
                items={job.state_history.map((t) => ({
                  title: `${STATE_LABEL[t.from_state]} → ${STATE_LABEL[t.to_state]}`,
                  detail: t.note,
                  time: clockTime(t.at),
                  tone:
                    t.to_state === 'HUMAN_REVIEW'
                      ? 'warn'
                      : t.to_state === 'FAILED'
                        ? 'risk'
                        : t.to_state === 'COMPLETED'
                          ? 'ok'
                          : 'brand',
                }))}
              />
            </div>
          </Card>
        </div>

        {/* Right — the reasoning */}
        <div className="space-y-5">
          <Card>
            <CardHeader title="Agent decision" icon={<Cpu size={16} />} />
            {decision ? (
              <div className="mt-4 space-y-4">
                <DecisionBadge decision={decision.decision} />
                <blockquote className="rounded-lg border-l-2 border-brand-400 bg-surface-sunken p-3 text-[12.5px] leading-snug text-ink-700">
                  {decision.reason}
                </blockquote>
                <ConfidenceMeter value={decision.confidence} />
                <dl className="border-t border-line pt-3">
                  <FieldRow label="Decision" value={decision.decision} mono />
                  <FieldRow
                    label="Human review"
                    value={decision.human_review_required ? 'required' : 'not required'}
                  />
                  <FieldRow
                    label="Ambiguity"
                    value={
                      decision.ambiguity_type ? (
                        <span className="font-mono text-[11px]">{decision.ambiguity_type}</span>
                      ) : (
                        '—'
                      )
                    }
                  />
                  <FieldRow label="Policy version" value={decision.policy_version ?? '—'} mono />
                </dl>
              </div>
            ) : (
              <EmptyState title="Not evaluated yet" detail="This job has not reached the policy-check stage." />
            )}
          </Card>

          <Card className="bg-rail-900 text-rail-200" padded>
            <div className="flex items-center gap-2">
              <ScrollText size={14} className="text-brand-400" />
              <h3 className="text-[12.5px] font-bold text-white">Audit provenance</h3>
            </div>
            <dl className="mt-3 space-y-1.5 font-mono text-[11px]">
              {[
                ['job_id', job.job_id],
                ['workflow', job.workflow],
                ['state', job.state],
                ['decision', decision?.decision ?? '—'],
                ['policy', decision?.policy_version ?? '—'],
                ['record', rec.record_id],
              ].map(([k, v]) => (
                <div key={k} className="flex items-center justify-between gap-3">
                  <dt className="text-rail-400">{k}</dt>
                  <dd className="truncate text-white">{v}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 border-t border-rail-700 pt-2.5 text-[10.5px] leading-snug text-rail-400">
              The LLM layer is not wired yet. These decisions come from the deterministic prototype
              policy, exactly as they will when PydanticAI is added — same schema, same gates.
            </p>
          </Card>

          <Card>
            <CardHeader title="Next step" />
            <div
              className={cx(
                'mt-3 rounded-lg border p-3.5 text-[12.5px] leading-snug',
                isApprove ? 'border-ok-100 bg-ok-50 text-ok-700' : 'border-warn-100 bg-warn-50 text-warn-700',
              )}
            >
              {isApprove ? (
                <>
                  Decision <strong>APPROVE</strong> routes to <strong>EXECUTING</strong>. Playwright
                  will click 承認, submit, then re-read the status to verify.
                </>
              ) : (
                <>
                  Decision <strong>REVIEW</strong> routes to <strong>HUMAN_REVIEW</strong>. The
                  platform will not act until a person decides.
                </>
              )}
            </div>
            <Button
              className="mt-3 w-full"
              variant={isApprove ? 'dark' : 'secondary'}
              onClick={() =>
                navigate(isApprove ? `/execution/${job.job_id}` : `/review/${job.job_id}`)
              }
            >
              {isApprove ? 'Open execution view' : 'Open human review'}
            </Button>
          </Card>
        </div>
      </div>
    </>
  )
}
