# Back-Office Automation Agent — frontend

Operations console for the Step 3 prototype. React 19 + Vite + TypeScript +
Tailwind v4. Separate from the Phase 1/2 analysis code, which is untouched.

**Stage: connected, two workflows.** Every screen reads live data from the FastAPI
backend. Runs started here call the real agent, drive a real browser, and show real
measured outcomes. Leave Approval and Payroll Confirmation share every screen — the
queue, the policy gates, the execution trace, the review form and the audit trail
are workflow-neutral, and the per-workflow field differences live in
`src/lib/record.ts`.

## Run

The backend must be running first (see `../backend/README.md`) — Vite proxies
`/api` to `http://127.0.0.1:8000`.

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Other scripts: `npm run build`, `npm run test`, `npm run typecheck`, `npm run lint`.

## Screens

| Route | Screen | What it shows |
|---|---|---|
| `/` | Overview & Metrics | Pipeline strip, KPIs from real runs, workflow cards with Phase 2 evidence, recent decisions, review queue, decision split, connectors |
| `/queue` | Workflow Task Queue | Every record from **both** queues with its live HR status, workflow label and provenance, plus the **Run agent** action that starts a real run |
| `/agent`, `/agent/:jobId` | Agent Policy & Decision | Record fields, policy gates (pass/fail/not-evaluable), decision + confidence, state transitions, audit provenance |
| `/execution`, `/execution/:jobId` | Step Automation Execution | The deterministic steps Playwright actually performed, before→after status, verification outcome |
| `/review`, `/review/:jobId` | Human Review Queue | Escalation cards, why it stopped, operator determination form with mandatory audit note |
| `/history` | Audit & Run History | Real runs with measured durations, throughput, workflow split |

Clicking a task routes to wherever it currently sits in the pipeline: escalated →
review, executed → execution, otherwise the agent view. A record nobody has run
yet has no job to open — run it first.

## Driving a demo from here

1. Start the backend, then `npm run dev`.
2. Open `/queue`. Every record is **Queued** — nothing has run.
3. **Run agent** on `DEMO-LV-001`. Every gate passes, so it auto-approves,
   Playwright performs the action, and verification confirms the status changed.
   You land on the execution trace.
4. **Run agent** on `P1-07046967-001` — the screenshot-confirmed *payroll* record.
   It auto-confirms, which reproduces the action an operator was actually observed
   taking in Dataset B. This is the strongest single demo in the prototype.
5. **Run agent** on `P2-07048822-006` — the screenshot-confirmed *leave* record. It
   escalates, because Dataset B showed whether prior approval was *required*, never
   whether it was *obtained*. You land in human review.
6. Choose a determination, write the mandatory audit note, confirm. The run happens
   then — your authorisation is what releases it to the executor.
7. **Run agent** on `DEMO-PAY-REVIEW` for the safety case: the amount exceeds the
   configured prototype limit, so a deterministic gate fails and **nothing touches
   the browser** until a human authorises it.
8. `/history` shows every run, both workflows, with real measured durations.

Watch it work by starting the backend with `PLAYWRIGHT_HEADLESS=false`.

## Structure

```
src/
├── types/index.ts          TS mirrors of the backend Pydantic models (1:1)
├── services/api.ts         the ONLY place components fetch from
├── hooks/useAsync.ts       loading / error / reload for every screen
├── lib/
│   ├── format.ts           formatters + status→tone maps
│   └── record.ts           workflow-neutral record rendering (fields, reference note)
├── components/
│   ├── ui/                 Card, Badge, Button, StatCard, Table, Tabs, states…
│   ├── charts/             Donut, Sparkline, StackedBars, MiniRing (hand-rolled SVG)
│   ├── domain/             PipelineStrip, PolicyGateCard, DecisionBadge, ProvenanceBadge…
│   └── layout/AppShell.tsx sidebar + topbar + page header
├── pages/                  one file per screen
└── __tests__/
    ├── screens.test.tsx    render tests that mount every screen
    └── fixtures.ts         test data (was the old mock service)
```

## The backend connection

Components never call `fetch` directly — they go through `src/services/api.ts`,
which is why connecting the whole console to the live backend was a change in one
file. Types in `src/types/` are copied from the backend models; change both together.

The backend exposes jobs rather than pre-chewed view models, so screen-shaped
things — queue stages, run-history rows, dashboard counters — are derived in
`api.ts` from real jobs. **Nothing there invents a number.** If no job has run, the
counters are zero and the screens show an empty system.

## Where the numbers come from

- **Measured** — everything on the KPI, execution and history screens comes from
  runs this backend actually performed. Durations are measured, never estimated.
- **Phase 2 evidence** — workflow cards (23 leave executions / 18.63 observed
  minutes; 39 payroll / 30.16) come from
  `phase2/results/automation_candidates.csv`. These are historical measurements
  of humans, not prototype run metrics, and the UI keeps them visibly separate.
- **Still a stand-in** — the target system is a mock HR application, and the
  records are demo data. Every screen that could be mistaken for production says so.
- **Provenance is visible**: observed / list-observed / synthetic are distinct
  badges, and synthetic records are all `DEMO-`-prefixed.

Two evidence-driven rules surface in the interface rather than hiding in config:
auto-rejection is disabled (the 差戻し control was never observed being used, so a
rejection can only be released by a human), and the grounded record escalates
because Dataset B showed whether prior approval was *required*, never whether it
was *obtained*.

## Tests

`npm run test` mounts all six screens in jsdom, waits for data, and asserts the
populated state — not just that components import. It also guards the data
integrity rules above (provenance mix, grounded record fidelity, `DEMO-` prefix,
REVIEW ⇒ human review) and the payroll workflow's own paths (both queues in one
table, the five payroll gates, the over-limit escalation, the confirmed execution,
and that a hold is never auto-executed). 23 tests.

`services/api` is replaced with `__tests__/fixtures.ts` in these tests. That keeps
what they are for — proving every screen renders without crashing — while leaving
the backend contract to the Python suite, where it is checked against a real
server and a real browser.

Three bugs were found this way and fixed: a Rules-of-Hooks violation in
`AuditHistory` (a `useMemo` after an early return, which crashed the page as soon
as data loaded), a queue footer that read "Showing 0 of 0 tasks" while loading, and
— once the console went live — `/api/leave-requests` still serving the seed file,
so approved records kept presenting as pending.
