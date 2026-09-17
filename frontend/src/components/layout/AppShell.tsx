import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  Activity,
  Bell,
  Bot,
  ChevronRight,
  Cpu,
  FileClock,
  LayoutGrid,
  ListChecks,
  PlayCircle,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  UserCheck,
} from 'lucide-react'
import { Dot, cx } from '@/components/ui'
import { useAsync } from '@/hooks/useAsync'
import { fetchDashboard, fetchWorkflows } from '@/services/api'

const NAV = [
  { to: '/', label: 'Overview & Metrics', icon: LayoutGrid, end: true },
  { to: '/queue', label: 'Workflow Task Queue', icon: ListChecks, badgeKey: 'queue' },
  { to: '/agent', label: 'Agent Policy & Decision', icon: Cpu, badgeKey: 'agent' },
  { to: '/execution', label: 'Step Automation Execution', icon: PlayCircle },
  { to: '/review', label: 'Human Review Queue', icon: UserCheck, badgeKey: 'review' },
  { to: '/history', label: 'Audit & Run History', icon: FileClock },
] as const

/**
 * Workflows the platform does NOT implement. Everything it does implement is read
 * from the backend below, so this list cannot drift out of date the way a
 * hardcoded one did.
 */
const UNSCOPED_WORKFLOWS = [
  { name: 'Expense Claims', status: 'Not scoped', tone: 'neutral' as const },
]

function Sidebar() {
  // Live counters. Before any job has run these are all zero, and the nav simply
  // shows no badges - which is the correct picture of an idle system.
  const { data } = useAsync(fetchDashboard, [])
  const { data: definitions } = useAsync(fetchWorkflows, [])
  const m = data?.metrics

  const workflowLinks = [
    ...(definitions ?? []).map((w) => ({
      name: w.name,
      status: w.implemented ? 'Active' : 'Declared',
      tone: (w.implemented ? 'ok' : 'warn') as 'ok' | 'warn' | 'neutral',
    })),
    ...UNSCOPED_WORKFLOWS,
  ]
  const badges: Record<string, number> = {
    queue: m ? m.queued + m.inFlight : 0,
    agent: m ? m.inFlight : 0,
    review: m ? m.humanReview : 0,
  }

  return (
    <aside className="flex w-[264px] shrink-0 flex-col bg-rail-900 text-rail-200">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
          <Bot size={17} />
        </span>
        <div className="min-w-0">
          <p className="truncate text-[14px] font-bold text-white leading-tight">
            Attention AI
          </p>
          <p className="flex items-center gap-1.5 text-[11px] text-rail-400">
            <Dot tone="ok" /> Step 3 prototype
          </p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4" aria-label="Primary">
        <p className="label-xs px-2 pb-2 pt-3 text-rail-400">Orchestration Engine</p>
        <ul className="space-y-0.5">
          {NAV.map((item) => {
            const Icon = item.icon
            const badge = 'badgeKey' in item ? badges[item.badgeKey as string] : undefined
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={'end' in item ? item.end : false}
                  className={({ isActive }) =>
                    cx(
                      'flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12.5px] font-medium transition-colors',
                      isActive
                        ? 'bg-rail-800 text-white'
                        : 'text-rail-300 hover:bg-rail-850 hover:text-white',
                    )
                  }
                >
                  <Icon size={15} className="shrink-0" />
                  <span className="flex-1 truncate">{item.label}</span>
                  {badge ? (
                    <span className="rounded-md bg-brand-600 px-1.5 py-0.5 text-[10.5px] font-bold tnum text-white">
                      {badge}
                    </span>
                  ) : null}
                </NavLink>
              </li>
            )
          })}
        </ul>

        <p className="label-xs px-2 pb-2 pt-6 text-rail-400">Workflows</p>
        <ul className="space-y-0.5">
          {workflowLinks.map((w) => (
            <li
              key={w.name}
              className="flex items-center justify-between rounded-lg px-2.5 py-1.5 text-[12.5px]"
            >
              <span className="flex items-center gap-2 text-rail-200">
                <Dot tone={w.tone} />
                {w.name}
              </span>
              <span className="text-[10.5px] text-rail-400">{w.status}</span>
            </li>
          ))}
        </ul>
      </nav>

      <div className="mx-3 mb-3 rounded-xl bg-rail-850 p-3.5">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-[12px] font-semibold text-white">
            <Activity size={13} className="text-ok-500" />
            Agent runtime
          </span>
          <span className="text-[10.5px] font-semibold text-ok-500">Live</span>
        </div>
        <dl className="mt-2.5 space-y-1.5">
          <div className="flex justify-between text-[11.5px]">
            <dt className="text-rail-400">Actionable records</dt>
            <dd className="tnum font-semibold text-white">{m?.pendingRecords ?? '—'}</dd>
          </div>
          <div className="flex justify-between text-[11.5px]">
            <dt className="text-rail-400">Awaiting human</dt>
            <dd className="tnum font-semibold text-white">{m?.humanReview ?? '—'}</dd>
          </div>
        </dl>
        <p className="mt-2.5 border-t border-rail-700 pt-2.5 font-mono text-[10px] leading-snug text-rail-400">
          Groq decision layer · Playwright executor · independent verification
        </p>
      </div>
    </aside>
  )
}

const CRUMBS: Record<string, string> = {
  '/': 'Overview & Metrics',
  '/queue': 'Workflow Task Queue',
  '/agent': 'Agent Policy & Decision',
  '/execution': 'Step Automation Execution',
  '/review': 'Human Review Queue',
  '/history': 'Audit & Run History',
}

function TopBar() {
  const { pathname } = useLocation()
  const crumb =
    CRUMBS[pathname] ??
    (pathname.startsWith('/agent')
      ? 'Agent Policy & Decision'
      : pathname.startsWith('/execution')
        ? 'Step Automation Execution'
        : pathname.startsWith('/review')
          ? 'Human Review Queue'
          : 'Operational Console')

  return (
    <header className="sticky top-0 z-20 flex items-center gap-4 border-b border-line bg-surface px-6 py-3">
      <nav className="flex items-center gap-2 text-[13px] text-ink-400" aria-label="Breadcrumb">
        <span>Platform</span>
        <ChevronRight size={13} />
        <span className="font-semibold text-ink-900">{crumb}</span>
      </nav>

      <span className="ml-1 inline-flex items-center gap-1.5 rounded-full border border-line bg-canvas px-2.5 py-1 text-[11.5px] font-semibold text-ink-500">
        <Dot tone="brand" pulse />
        Agent mode: policy-bounded
      </span>

      <div className="relative ml-auto hidden w-[300px] lg:block">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" />
        <input
          type="search"
          placeholder="Search records, employee ID, task…"
          className="w-full rounded-lg border border-line bg-canvas py-1.5 pl-9 pr-10 text-[12.5px] text-ink-900 placeholder:text-ink-300 focus:border-brand-400 focus:bg-surface focus:outline-none"
        />
        <kbd className="absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-line-strong bg-surface px-1.5 py-0.5 font-mono text-[10px] text-ink-400 xl:block">
          ⌘K
        </kbd>
      </div>

      <div className="flex items-center gap-1">
        <button
          type="button"
          className="relative rounded-lg p-2 text-ink-400 transition-colors hover:bg-canvas hover:text-ink-900"
          aria-label="Notifications"
        >
          <Bell size={16} />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-risk-500" />
        </button>
        <button
          type="button"
          className="rounded-lg p-2 text-ink-400 transition-colors hover:bg-canvas hover:text-ink-900"
          aria-label="Settings"
        >
          <SlidersHorizontal size={16} />
        </button>
      </div>

      <div className="flex items-center gap-2.5 border-l border-line pl-4">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-[11.5px] font-bold text-brand-700">
          OP
        </span>
        <div className="hidden leading-tight sm:block">
          <p className="text-[12.5px] font-semibold text-ink-900">Operations</p>
          <p className="text-[11px] text-ink-400">Reviewer</p>
        </div>
      </div>
    </header>
  )
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-canvas">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto max-w-[1420px]">{children}</div>
        </main>
      </div>
    </div>
  )
}

export function PageHeader({
  title,
  subtitle,
  badge,
  meta,
  actions,
}: {
  title: string
  subtitle?: string
  badge?: ReactNode
  meta?: ReactNode
  actions?: ReactNode
}) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-[26px] font-extrabold tracking-tight text-ink-900">{title}</h1>
          {badge}
        </div>
        {subtitle && <p className="mt-1.5 max-w-3xl text-[13px] text-ink-500">{subtitle}</p>}
        {meta && (
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11.5px] text-ink-400">
            {meta}
          </div>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export { ShieldCheck }
