/**
 * Shared UI primitives. Every screen composes these rather than restyling
 * cards/badges/buttons locally, so the console stays visually consistent.
 */

import type { ReactNode } from 'react'
import { AlertTriangle, Inbox, Loader2 } from 'lucide-react'
import type { ToneName } from '@/lib/format'
import { avatarTone, initials } from '@/lib/format'

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}

/* ---- Card --------------------------------------------------------------- */

export function Card({
  children,
  className,
  padded = true,
}: {
  children: ReactNode
  className?: string
  padded?: boolean
}) {
  return (
    <section
      className={cx(
        'rounded-xl border border-line bg-surface shadow-[0_1px_2px_rgba(15,17,23,0.04)]',
        padded && 'p-5',
        className,
      )}
    >
      {children}
    </section>
  )
}

export function CardHeader({
  title,
  subtitle,
  icon,
  action,
  className,
}: {
  title: ReactNode
  subtitle?: ReactNode
  icon?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cx('flex items-start justify-between gap-4', className)}>
      <div className="flex items-start gap-2.5 min-w-0">
        {icon && <span className="mt-0.5 text-brand-600 shrink-0">{icon}</span>}
        <div className="min-w-0">
          <h2 className="text-[15px] font-bold text-ink-900 leading-tight">{title}</h2>
          {subtitle && <p className="mt-1 text-[12.5px] text-ink-500 leading-snug">{subtitle}</p>}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}

/* ---- Badge -------------------------------------------------------------- */

const TONE_CLASS: Record<ToneName, string> = {
  neutral: 'bg-canvas text-ink-500 border-line-strong',
  brand: 'bg-brand-50 text-brand-700 border-brand-200',
  ok: 'bg-ok-50 text-ok-700 border-ok-100',
  warn: 'bg-warn-50 text-warn-700 border-warn-100',
  risk: 'bg-risk-50 text-risk-700 border-risk-100',
  info: 'bg-info-50 text-info-500 border-info-100',
}

const DOT_CLASS: Record<ToneName, string> = {
  neutral: 'bg-ink-300',
  brand: 'bg-brand-600',
  ok: 'bg-ok-500',
  warn: 'bg-warn-500',
  risk: 'bg-risk-500',
  info: 'bg-info-500',
}

export function Badge({
  children,
  tone = 'neutral',
  dot = false,
  pulse = false,
  className,
}: {
  children: ReactNode
  tone?: ToneName
  dot?: boolean
  pulse?: boolean
  className?: string
}) {
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-[3px] text-[11.5px] font-semibold whitespace-nowrap',
        TONE_CLASS[tone],
        className,
      )}
    >
      {dot && (
        <span
          className={cx('h-1.5 w-1.5 rounded-full', DOT_CLASS[tone], pulse && 'animate-pulse-dot')}
        />
      )}
      {children}
    </span>
  )
}

export function Dot({ tone = 'neutral', pulse }: { tone?: ToneName; pulse?: boolean }) {
  return (
    <span className={cx('h-2 w-2 rounded-full', DOT_CLASS[tone], pulse && 'animate-pulse-dot')} />
  )
}

/* ---- Button ------------------------------------------------------------- */

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'dark'

const BUTTON_CLASS: Record<ButtonVariant, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 border-transparent',
  dark: 'bg-ink-900 text-white hover:bg-rail-800 border-transparent',
  secondary: 'bg-surface text-ink-700 hover:bg-canvas border-line-strong',
  ghost: 'bg-transparent text-ink-500 hover:bg-canvas hover:text-ink-900 border-transparent',
  danger: 'bg-risk-50 text-risk-700 hover:bg-risk-100 border-risk-100',
}

export function Button({
  children,
  variant = 'secondary',
  icon,
  size = 'md',
  onClick,
  disabled,
  title,
  className,
  type = 'button',
}: {
  children?: ReactNode
  variant?: ButtonVariant
  icon?: ReactNode
  size?: 'sm' | 'md'
  onClick?: () => void
  disabled?: boolean
  title?: string
  className?: string
  type?: 'button' | 'submit'
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-lg border font-semibold transition-colors',
        'disabled:cursor-not-allowed disabled:opacity-45',
        size === 'sm' ? 'px-2.5 py-1.5 text-[12px]' : 'px-3.5 py-2 text-[13px]',
        BUTTON_CLASS[variant],
        className,
      )}
    >
      {icon}
      {children}
    </button>
  )
}

/* ---- Stat tile ---------------------------------------------------------- */

export function StatCard({
  label,
  value,
  delta,
  deltaTone = 'neutral',
  footnote,
  icon,
  visual,
}: {
  label: string
  value: ReactNode
  delta?: string
  deltaTone?: ToneName
  footnote?: ReactNode
  icon?: ReactNode
  visual?: ReactNode
}) {
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <span className="label-xs text-ink-400">{label}</span>
        {icon && <span className="text-ink-300">{icon}</span>}
      </div>
      <div className="flex items-end justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[28px] font-bold leading-none tnum text-ink-900">{value}</span>
          {delta && (
            <Badge tone={deltaTone} className="mb-0.5">
              {delta}
            </Badge>
          )}
        </div>
        {visual}
      </div>
      {footnote && <div className="text-[11.5px] text-ink-400 leading-snug">{footnote}</div>}
    </Card>
  )
}

/* ---- Avatar ------------------------------------------------------------- */

export function Avatar({
  name,
  size = 'md',
}: {
  name: string | null
  size?: 'sm' | 'md' | 'lg'
}) {
  const dim = size === 'sm' ? 'h-7 w-7 text-[10px]' : size === 'lg' ? 'h-12 w-12 text-[14px]' : 'h-9 w-9 text-[11.5px]'
  return (
    <span
      className={cx(
        'inline-flex shrink-0 items-center justify-center rounded-full font-bold',
        dim,
        avatarTone(name ?? 'unknown'),
      )}
      aria-hidden
    >
      {initials(name)}
    </span>
  )
}

/* ---- Progress ----------------------------------------------------------- */

export function ProgressBar({
  value,
  tone = 'brand',
  className,
  height = 'h-1.5',
}: {
  value: number
  tone?: ToneName
  className?: string
  height?: string
}) {
  return (
    <div className={cx('w-full overflow-hidden rounded-full bg-canvas', height, className)}>
      <div
        className={cx('h-full rounded-full animate-bar', DOT_CLASS[tone])}
        style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }}
      />
    </div>
  )
}

/* ---- Tabs --------------------------------------------------------------- */

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ id: T; label: string; count?: number; tone?: ToneName }>
  active: T
  onChange: (id: T) => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-1 rounded-xl border border-line bg-surface p-1">
      {tabs.map((tab) => {
        const isActive = tab.id === active
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={cx(
              'inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold transition-colors',
              isActive ? 'bg-canvas text-ink-900' : 'text-ink-500 hover:text-ink-900 hover:bg-canvas/60',
            )}
          >
            {tab.tone && <Dot tone={tab.tone} />}
            {tab.label}
            {tab.count !== undefined && (
              <span className={cx('tnum text-[11.5px]', isActive ? 'text-ink-500' : 'text-ink-300')}>
                {tab.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

/* ---- Table -------------------------------------------------------------- */

export function Table({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx('overflow-x-auto', className)}>
      <table className="w-full border-collapse text-[13px]">{children}</table>
    </div>
  )
}

export function Th({
  children,
  align = 'left',
  className,
}: {
  children?: ReactNode
  align?: 'left' | 'right' | 'center'
  className?: string
}) {
  return (
    <th
      className={cx(
        'label-xs whitespace-nowrap border-b border-line px-3 py-2.5 text-ink-400',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
        align === 'left' && 'text-left',
        className,
      )}
    >
      {children}
    </th>
  )
}

export function Td({
  children,
  align = 'left',
  className,
}: {
  children?: ReactNode
  align?: 'left' | 'right' | 'center'
  className?: string
}) {
  return (
    <td
      className={cx(
        'border-b border-line px-3 py-2.5 align-middle text-ink-700',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
        className,
      )}
    >
      {children}
    </td>
  )
}

/* ---- Mono chip ---------------------------------------------------------- */

export function Mono({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cx('font-mono text-[12px] tnum', className)}>{children}</span>
}

export function IdChip({ children, tone = 'brand' }: { children: ReactNode; tone?: ToneName }) {
  return (
    <span
      className={cx(
        'inline-block rounded-md border px-2 py-0.5 font-mono text-[11.5px] font-semibold',
        TONE_CLASS[tone],
      )}
    >
      {children}
    </span>
  )
}

/* ---- States ------------------------------------------------------------- */

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2.5 py-16 text-ink-400">
      <Loader2 size={16} className="animate-spin" />
      <span className="text-[13px]">{label}</span>
    </div>
  )
}

export function EmptyState({
  title,
  detail,
  icon,
}: {
  title: string
  detail?: string
  icon?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-14 text-center">
      <span className="text-ink-300">{icon ?? <Inbox size={22} />}</span>
      <p className="text-[13.5px] font-semibold text-ink-700">{title}</p>
      {detail && <p className="max-w-sm text-[12.5px] text-ink-400">{detail}</p>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-center">
      <span className="text-risk-500">
        <AlertTriangle size={22} />
      </span>
      <p className="text-[13.5px] font-semibold text-ink-900">Could not load this view</p>
      <p className="max-w-md font-mono text-[12px] text-ink-400">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  )
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-9 animate-pulse rounded-lg bg-canvas" />
      ))}
    </div>
  )
}
