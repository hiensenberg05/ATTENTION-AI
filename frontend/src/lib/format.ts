import type { DecisionType, JobState, QueueStage, VerificationStatus } from '@/types'

export function pct(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`
}

export function seconds(value: number | null | undefined): string {
  if (value == null) return '—'
  return value < 1 ? `${Math.round(value * 1000)}ms` : `${value.toFixed(1)}s`
}

export function ms(value: number | null | undefined): string {
  if (value == null) return '—'
  return value < 1000 ? `${value}ms` : `${(value / 1000).toFixed(1)}s`
}

export function relativeTime(iso: string, now = new Date()): string {
  const diff = now.getTime() - new Date(iso).getTime()
  const mins = Math.round(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

export function clockTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function shortDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  })
}

export function jpy(amount: string | null): string {
  if (!amount) return '—'
  return `¥${Number(amount).toLocaleString('en-US')}`
}

/** Two-letter initials for the avatar chips. Handles Japanese names too. */
export function initials(name: string | null): string {
  if (!name) return '??'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

/** Deterministic avatar colour so the same person is always the same colour. */
export function avatarTone(seed: string): string {
  const tones = [
    'bg-brand-100 text-brand-700',
    'bg-info-100 text-info-500',
    'bg-ok-100 text-ok-700',
    'bg-warn-100 text-warn-700',
    'bg-risk-100 text-risk-700',
    'bg-rail-800 text-rail-200',
  ]
  let hash = 0
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0
  return tones[hash % tones.length]
}

export const STATE_LABEL: Record<JobState, string> = {
  START: 'Queued',
  LOADING: 'Loading',
  VALIDATING: 'Validating',
  ANALYZING: 'Analyzing',
  POLICY_CHECK: 'Policy check',
  HUMAN_REVIEW: 'Human review',
  EXECUTING: 'Executing',
  VERIFYING: 'Verifying',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
}

export type ToneName = 'neutral' | 'brand' | 'ok' | 'warn' | 'risk' | 'info'

export const STATE_TONE: Record<JobState, ToneName> = {
  START: 'neutral',
  LOADING: 'neutral',
  VALIDATING: 'brand',
  ANALYZING: 'brand',
  POLICY_CHECK: 'brand',
  HUMAN_REVIEW: 'warn',
  EXECUTING: 'info',
  VERIFYING: 'info',
  COMPLETED: 'ok',
  FAILED: 'risk',
}

export const STAGE_TONE: Record<QueueStage, ToneName> = {
  Queued: 'neutral',
  'Agent Evaluating': 'brand',
  'Pending Human Sign-off': 'warn',
  Executing: 'info',
  Verifying: 'info',
  Completed: 'ok',
  Failed: 'risk',
}

export const DECISION_TONE: Record<DecisionType, ToneName> = {
  APPROVE: 'ok',
  REJECT: 'risk',
  REVIEW: 'warn',
}

export const DECISION_LABEL: Record<DecisionType, string> = {
  APPROVE: 'Approve',
  REJECT: 'Reject',
  REVIEW: 'Needs review',
}

export const VERIFICATION_TONE: Record<VerificationStatus, ToneName> = {
  NOT_ATTEMPTED: 'neutral',
  VERIFIED: 'ok',
  FAILED: 'risk',
  NOT_APPLICABLE: 'neutral',
}

export const PROVENANCE_LABEL: Record<string, string> = {
  dataset_b_observed: 'Observed in Dataset B',
  dataset_b_list_observed: 'List-observed in Dataset B',
  synthetic_demo: 'Synthetic demo record',
}
