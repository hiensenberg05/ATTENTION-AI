/**
 * The five prototype run metrics, as they go into the report.
 *
 * Every figure comes from `GET /api/metrics`, computed in Python from real runs.
 * Nothing on this panel is re-derived in the browser, so the screen and the report
 * cannot quietly disagree.
 *
 * Two presentation rules the rest of the project depends on:
 *
 *   1. A null rate renders as "no data", never as 0%. An idle system has not
 *      achieved a 0% success rate; it has not been measured.
 *   2. Prototype latency and the Dataset B human baseline are shown side by side
 *      and never subtracted. The caveat travels with them, on screen.
 */

import {
  AlertTriangle,
  CheckCircle2,
  Gauge,
  ShieldCheck,
  Timer,
  UserCheck,
} from 'lucide-react'
import { Card, CardHeader, Badge, Mono, cx } from '@/components/ui'
import type { PrototypeMetrics, Rate } from '@/types'

/** A rate, or an explicit statement that nothing has been measured. */
function rate(value: Rate, digits = 1): string {
  return value === null ? 'no data' : `${(value * 100).toFixed(digits)}%`
}

function secs(value: number | null): string {
  return value === null ? '—' : `${value.toFixed(2)}s`
}

function Metric({
  n,
  title,
  value,
  tone = 'ink',
  icon,
  lines,
  note,
}: {
  n: number
  title: string
  value: string
  tone?: 'ink' | 'ok' | 'warn' | 'risk'
  icon: React.ReactNode
  lines: Array<[string, string]>
  note?: string
}) {
  const valueTone = {
    ink: 'text-ink-900',
    ok: 'text-ok-700',
    warn: 'text-warn-700',
    risk: 'text-risk-700',
  }[tone]

  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded bg-canvas text-[10px] font-bold text-ink-400 tnum">
            {n}
          </span>
          <span className="text-[12.5px] font-semibold text-ink-700">{title}</span>
        </div>
        <span className="text-ink-300">{icon}</span>
      </div>

      <p className={cx('mt-2 text-[24px] font-bold tnum leading-none', valueTone)}>
        {value}
      </p>

      <dl className="mt-3 space-y-1">
        {lines.map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-3 text-[11.5px]">
            <dt className="text-ink-400">{k}</dt>
            <dd className="tnum font-semibold text-ink-700">{v}</dd>
          </div>
        ))}
      </dl>

      {note && (
        <p className="mt-2.5 border-t border-line pt-2 text-[10.5px] leading-snug text-ink-400">
          {note}
        </p>
      )}
    </div>
  )
}

export function PrototypeMetricsPanel({ m }: { m: PrototypeMetrics }) {
  const { sample, automation_success, verification, automation_rate, execution_latency, safety } = m
  const probe = safety.adversarial_probe
  const held = probe.leaked.length === 0 && safety.policy_bypasses === 0

  return (
    <Card>
      <CardHeader
        title="Prototype run metrics"
        subtitle={`Measured from ${sample.total_runs} run${sample.total_runs === 1 ? '' : 's'} in this process — ${sample.execution_attempts} reached the browser`}
        icon={<Gauge size={16} />}
        action={
          <Badge tone={held ? 'ok' : 'risk'} dot>
            {held ? 'Safety claim holds' : 'Safety claim VIOLATED'}
          </Badge>
        }
      />

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Metric
          n={1}
          title="Automation success rate"
          value={rate(automation_success.rate)}
          tone="ok"
          icon={<CheckCircle2 size={15} />}
          lines={[
            ['Verified', String(automation_success.verified)],
            ['Runs that acted', String(automation_success.attempted)],
          ]}
          note="Escalated jobs are excluded — they never attempted an action, so they cannot fail at one."
        />

        <Metric
          n={2}
          title="Verification"
          value={`${verification.verified} / ${automation_success.attempted}`}
          tone={verification.failed > 0 ? 'warn' : 'ok'}
          icon={<ShieldCheck size={15} />}
          lines={[
            ['Verified', String(verification.verified)],
            ['Failed verification', String(verification.failed)],
            ['Never attempted', String(verification.not_attempted)],
          ]}
          note="Expected vs observed business state, re-read independently from the queue screen — not the executor reporting its own success."
        />

        <Metric
          n={3}
          title="Automation / review rate"
          value={rate(automation_rate.automation_rate)}
          icon={<UserCheck size={15} />}
          lines={[
            ['Completed with no human', String(automation_rate.completed_without_human)],
            ['Required human review', String(automation_rate.required_human_review)],
            ['Review rate', rate(automation_rate.review_rate)],
            ['Failed', String(automation_rate.failed)],
          ]}
          note="Escalation is a designed outcome, not a failure: the review rate is a property of the evidence, not of the agent."
        />

        <Metric
          n={4}
          title="Execution latency"
          value={secs(execution_latency.prototype_seconds.median)}
          icon={<Timer size={15} />}
          lines={[
            ['Mean', secs(execution_latency.prototype_seconds.mean)],
            [
              'Range',
              execution_latency.prototype_seconds.n
                ? `${secs(execution_latency.prototype_seconds.fastest)}–${secs(execution_latency.prototype_seconds.slowest)}`
                : '—',
            ],
            ['Runs measured', String(execution_latency.prototype_seconds.n)],
          ]}
          note="Measured, never estimated."
        />

        <Metric
          n={5}
          title="Safety — policy bypasses"
          value={String(safety.policy_bypasses)}
          tone={safety.policy_bypasses === 0 ? 'ok' : 'risk'}
          icon={held ? <ShieldCheck size={15} /> : <AlertTriangle size={15} />}
          lines={[
            ['Guard interventions', String(safety.guard_interventions)],
            ['Model stopped from acting', String(safety.model_wanted_to_act_but_was_stopped)],
            [
              'Escalated but executed',
              String(safety.escalated_but_executed_without_authorisation),
            ],
          ]}
          note={safety.observed_only_caveat}
        />

        <Metric
          n={5}
          title="Safety — adversarial probe"
          value={rate(probe.hold_rate, 0)}
          tone={probe.leaked.length === 0 ? 'ok' : 'risk'}
          icon={<ShieldCheck size={15} />}
          lines={[
            ['Records probed', String(probe.records_probed)],
            ['Policy wanted escalated', String(probe.records_the_policy_wanted_escalated)],
            ['Held by the guard', String(probe.held_by_the_guard)],
            ['Leaked', String(probe.leaked.length)],
          ]}
          note="Run live: every record is re-evaluated with a maximally hostile model draft (APPROVE, confidence 1.0). Every one the policy wanted escalated must come back REVIEW."
        />
      </div>

      {/* Metric 4's other half. Deliberately a separate block, so the two
          populations are never read as one subtraction. */}
      <div className="mt-4 rounded-lg border border-warn-100 bg-warn-50 p-4">
        <p className="text-[12px] font-bold text-warn-700">
          Prototype latency vs the Dataset B human baseline — NOT a savings figure
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {Object.entries(execution_latency.observed_human_baseline).map(([wf, base]) => {
            const mine = m.by_workflow[wf]?.prototype_latency_seconds
            return (
              <div key={wf} className="rounded-lg border border-line bg-surface p-3">
                <p className="text-[11.5px] font-semibold text-ink-700">
                  {wf === 'LEAVE_APPROVAL' ? 'Leave Approval' : 'Payroll Confirmation'}
                </p>
                <dl className="mt-1.5 space-y-1 text-[11.5px]">
                  <div className="flex justify-between gap-3">
                    <dt className="text-ink-400">Prototype (median, measured)</dt>
                    <dd className="tnum font-semibold text-ink-900">
                      {secs(mine?.median ?? null)}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-ink-400">Human clean instance</dt>
                    <dd className="tnum font-semibold text-ink-700">
                      {base.clean_instance_seconds.toFixed(2)}s
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-ink-400">Human family median</dt>
                    <dd className="tnum font-semibold text-ink-700">
                      {base.family_median_seconds.toFixed(2)}s
                    </dd>
                  </div>
                </dl>
                <Mono className="mt-1.5 block text-[10px] text-ink-300">{base.segment}</Mono>
              </div>
            )
          })}
        </div>
        <p className="mt-3 text-[11px] leading-snug text-warn-700">
          {execution_latency.caveat}
        </p>
      </div>
    </Card>
  )
}
