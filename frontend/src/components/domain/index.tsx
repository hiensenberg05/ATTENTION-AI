/**
 * Domain components — pieces that encode this product's actual concepts
 * (pipeline stages, policy gates, decisions, provenance) rather than generic UI.
 */

import type { ReactNode } from 'react'
import { AlertTriangle, Check, CircleHelp, FlaskConical, Minus, X } from 'lucide-react'
import type { DecisionType, JobState, PolicyCheck, Provenance, QueueStage } from '@/types'
import {
  DECISION_LABEL,
  DECISION_TONE,
  PROVENANCE_LABEL,
  STAGE_TONE,
  STATE_LABEL,
  STATE_TONE,
} from '@/lib/format'
import { Badge, Card, Dot, ProgressBar, cx } from '@/components/ui'

/* ---- Pipeline strip ------------------------------------------------------ */

/** The six deterministic stages, mapped to real JobStates from the backend. */
export const PIPELINE_STAGES: Array<{
  index: string
  label: string
  state: JobState
}> = [
  { index: '01', label: 'Load', state: 'LOADING' },
  { index: '02', label: 'Validate', state: 'VALIDATING' },
  { index: '03', label: 'Analyze', state: 'ANALYZING' },
  { index: '04', label: 'Policy check', state: 'POLICY_CHECK' },
  { index: '05', label: 'Execute', state: 'EXECUTING' },
  { index: '06', label: 'Verify', state: 'VERIFYING' },
]

export function PipelineStrip({
  counts,
  sublabels,
}: {
  counts: Record<string, number | string>
  sublabels: Record<string, string>
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
      {PIPELINE_STAGES.map((stage) => (
        <div
          key={stage.index}
          className="rounded-lg border border-line bg-surface-sunken px-3 py-2.5"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10.5px] font-semibold text-ink-300">
              {stage.index}
            </span>
            <Dot tone={STATE_TONE[stage.state]} />
          </div>
          <div className="mt-1.5 text-[17px] font-bold tnum leading-none text-ink-900">
            {counts[stage.state] ?? 0}
          </div>
          <div className="mt-1 text-[11px] font-semibold text-ink-700">{stage.label}</div>
          <div className="mt-0.5 text-[10.5px] text-ink-400 leading-tight">
            {sublabels[stage.state] ?? ''}
          </div>
        </div>
      ))}
    </div>
  )
}

/* ---- Badges -------------------------------------------------------------- */

export function StateBadge({ state, pulse }: { state: JobState; pulse?: boolean }) {
  return (
    <Badge tone={STATE_TONE[state]} dot pulse={pulse}>
      {STATE_LABEL[state]}
    </Badge>
  )
}

export function StageBadge({ stage }: { stage: QueueStage }) {
  const animated = stage === 'Agent Evaluating' || stage === 'Executing' || stage === 'Verifying'
  return (
    <Badge tone={STAGE_TONE[stage]} dot pulse={animated}>
      {stage}
    </Badge>
  )
}

export function DecisionBadge({
  decision,
  confidence,
}: {
  decision: DecisionType
  confidence?: number | null
}) {
  return (
    <Badge tone={DECISION_TONE[decision]} dot>
      {DECISION_LABEL[decision]}
      {confidence != null && (
        <span className="tnum font-normal opacity-70">{(confidence * 100).toFixed(1)}%</span>
      )}
    </Badge>
  )
}

/** Provenance is load-bearing in this project — never let a synthetic record
 *  look like observed evidence. */
export function ProvenanceBadge({ provenance }: { provenance: Provenance }) {
  const tone =
    provenance === 'dataset_b_observed'
      ? 'ok'
      : provenance === 'dataset_b_list_observed'
        ? 'info'
        : 'neutral'
  return (
    <Badge tone={tone} className="font-medium">
      {PROVENANCE_LABEL[provenance]}
    </Badge>
  )
}

/* ---- Policy gate --------------------------------------------------------- */

export function PolicyGateCard({ check, index }: { check: PolicyCheck; index: number }) {
  const state =
    check.passed === true ? 'pass' : check.passed === false ? 'fail' : 'unknown'

  const config = {
    pass: {
      tone: 'ok' as const,
      label: 'PASS',
      icon: <Check size={13} strokeWidth={3} />,
      ring: 'border-ok-100 bg-ok-50',
      iconWrap: 'bg-ok-500 text-white',
    },
    fail: {
      tone: 'risk' as const,
      label: 'FAIL',
      icon: <X size={13} strokeWidth={3} />,
      ring: 'border-risk-100 bg-risk-50',
      iconWrap: 'bg-risk-500 text-white',
    },
    unknown: {
      tone: 'warn' as const,
      label: 'NOT EVALUABLE',
      icon: <CircleHelp size={13} strokeWidth={2.5} />,
      ring: 'border-warn-100 bg-warn-50',
      iconWrap: 'bg-warn-500 text-white',
    },
  }[state]

  return (
    <div className={cx('rounded-lg border p-3.5', config.ring)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <span
            className={cx(
              'mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full',
              config.iconWrap,
            )}
          >
            {config.icon}
          </span>
          <div className="min-w-0">
            <p className="text-[13px] font-bold text-ink-900">
              Gate {index + 1}. {check.description}
            </p>
            {check.detail && (
              <p className="mt-1 text-[12px] leading-snug text-ink-500">{check.detail}</p>
            )}
            {check.source && (
              <p className="mt-1.5 font-mono text-[10.5px] text-ink-400">Source: {check.source}</p>
            )}
          </div>
        </div>
        <Badge tone={config.tone}>{config.label}</Badge>
      </div>
    </div>
  )
}

/* ---- Timeline ------------------------------------------------------------ */

export function Timeline({
  items,
}: {
  items: Array<{
    title: string
    detail?: ReactNode
    time?: string
    tone?: 'neutral' | 'brand' | 'ok' | 'warn' | 'risk' | 'info'
    active?: boolean
  }>
}) {
  return (
    <ol className="relative space-y-3.5 pl-5">
      <span className="absolute left-[5px] top-2 bottom-2 w-px bg-line" aria-hidden />
      {items.map((item, i) => (
        <li key={i} className="relative">
          <span className="absolute -left-5 top-1.5">
            <Dot tone={item.tone ?? 'brand'} pulse={item.active} />
          </span>
          <p className="text-[12.5px] font-semibold text-ink-900">{item.title}</p>
          {item.detail && <div className="mt-0.5 text-[11.5px] text-ink-500">{item.detail}</div>}
          {item.time && (
            <p className="mt-0.5 font-mono text-[10.5px] text-ink-400">{item.time}</p>
          )}
        </li>
      ))}
    </ol>
  )
}

/* ---- Demo-data notice ---------------------------------------------------- */

/**
 * Shown on every screen that displays fabricated operational numbers.
 * The whole project has been rigorous about not presenting invented figures as
 * measurements; the UI must not quietly break that.
 */
export function DemoDataNotice({ children }: { children?: ReactNode }) {
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-warn-100 bg-warn-50 px-3.5 py-2.5">
      <FlaskConical size={15} className="mt-px shrink-0 text-warn-700" />
      <p className="text-[12px] leading-snug text-warn-700">
        {children ?? (
          <>
            <strong className="font-bold">Prototype environment.</strong> Counters below are
            measured from real agent runs in this session, but the target system is a mock HR
            application standing in for the real one, and the records are demo data. Workflow
            evidence figures (executions, observed minutes) are Phase 2 measurements from Dataset B.
          </>
        )}
      </p>
    </div>
  )
}

/* ---- Record summary ------------------------------------------------------ */

export function FieldRow({
  label,
  value,
  mono,
  missing,
}: {
  label: string
  value: ReactNode
  mono?: boolean
  missing?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line py-2 last:border-0">
      <span className="shrink-0 text-[12px] text-ink-400">{label}</span>
      <span
        className={cx(
          'text-right text-[12.5px] font-semibold',
          mono && 'font-mono tnum',
          missing ? 'text-risk-500' : 'text-ink-900',
        )}
      >
        {missing ? 'missing' : value}
      </span>
    </div>
  )
}

export function AmbiguityCallout({
  reason,
  ambiguity,
}: {
  reason: string
  ambiguity: string | null
}) {
  return (
    <Card className="border-warn-100 bg-warn-50">
      <div className="flex items-start gap-2.5">
        <AlertTriangle size={16} className="mt-0.5 shrink-0 text-warn-700" />
        <div>
          <p className="text-[13px] font-bold text-warn-700">
            Autonomous execution paused
            {ambiguity && (
              <span className="ml-2 font-mono text-[11px] font-semibold opacity-80">
                {ambiguity.replace(/_/g, ' ')}
              </span>
            )}
          </p>
          <p className="mt-1 text-[12.5px] leading-snug text-warn-700/90">{reason}</p>
        </div>
      </div>
    </Card>
  )
}

export function ConfidenceMeter({ value, threshold = 0.8 }: { value: number; threshold?: number }) {
  const tone = value >= threshold ? 'ok' : value >= 0.5 ? 'warn' : 'risk'
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between">
        <span className="text-[11.5px] text-ink-400">Confidence</span>
        <span className="tnum text-[13px] font-bold text-ink-900">
          {(value * 100).toFixed(1)}%
        </span>
      </div>
      <div className="relative">
        <ProgressBar value={value} tone={tone} height="h-2" />
        <span
          className="absolute -top-0.5 h-3 w-px bg-ink-400"
          style={{ left: `${threshold * 100}%` }}
          title={`Auto-execution threshold ${(threshold * 100).toFixed(0)}%`}
        />
      </div>
      <p className="flex items-center gap-1 text-[10.5px] text-ink-400">
        <Minus size={9} /> auto-execution threshold {(threshold * 100).toFixed(0)}%
      </p>
    </div>
  )
}
