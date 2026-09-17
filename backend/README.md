# Back-Office Automation Agent — backend

Step 3 prototype for the IMbesideYou FDE assignment. Separate from the Phase 1/2
analysis code (`src/`, `phase1*/`, `phase2_dataset_b/`), which is frozen and untouched.

**Stage: two workflows live.** An LLM evaluates an explicit policy and returns a
structured decision, Python routes the job through a state machine, Playwright
performs the decided action in a mock HR system, and an independent re-read
verifies that the record actually changed.

Both **Leave Approval** and **Payroll Confirmation** run on the same pipeline. The
second workflow required no new orchestration, no new state machine, no second
agent and no second executor — only a workflow definition, a policy section, a set
of gates, a screen spec and one row in the registry.

> **AI decides. Python controls. Playwright executes. Verification proves the result.**

## Run

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

./.venv/Scripts/python.exe -m playwright install chromium       # one-time
./.venv/Scripts/python.exe -m uvicorn main:app --reload --port 8000
```

- API docs: <http://127.0.0.1:8000/docs>
- Mock HR system: <http://127.0.0.1:8000/mock-hr/leave-applications> and
  <http://127.0.0.1:8000/mock-hr/payroll-items>

Tests (64, including real-browser runs against a real server): `python -m pytest`

### Environment

Copy `.env.example` to `.env` at the repo root.

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | **Required for the LLM layer.** Read from the environment; never hardcoded, never logged, never returned by an endpoint. Without it the backend still runs — decisions fall back to the deterministic policy engine and are marked `decided_by="policy_engine_fallback"`. |
| `MOCK_HR_BASE_URL` | Where the executor drives the browser. Default `http://127.0.0.1:8000/mock-hr`. |
| `PLAYWRIGHT_HEADLESS` | `false` to watch the browser work during a demo. |
| `PLAYWRIGHT_TIMEOUT_MS` | Per-action timeout, default 10000. |

## Architecture

```
  record ──► policy_engine ──► decision_agent ──► guards ──► orchestrator ──► executor ──► verification
            (deterministic)     (Groq LLM)      (Python)    (state machine)  (Playwright)  (independent re-read)
                  │                  │              │             │                │              │
            PolicyCheck[]     LlmDecisionDraft  AgentDecision   JobState     ExecutionResult  VerificationStatus
```

**The LLM is called from exactly one place** — the `POLICY_CHECK` step — and its
answer is a value, not a command. It has no tools, never sees a URL or a selector,
and cannot decide that anything should be executed: `DECISION_ROUTES` does that.
One agent serves both workflows; there is no second prompt chain to keep in sync.

**The model may escalate; it may never de-escalate.** `guards.enforce` merges the
model's draft with the deterministic evaluation by taking the more conservative of
the two, then applies hard constraints the model cannot argue past. The policy
checks shown in the UI are always the deterministic ones — the model does not get
to author the audit trail.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness, counts, and whether the LLM layer is configured |
| GET | `/api/agent/health` | LLM configuration (never the key) |
| GET | `/api/workflows` | All defined workflows, with Phase 2 evidence and caveats |
| GET | `/api/workflows/{workflow}` | One workflow definition by type |
| GET | `/api/leave-requests` | The leave queue **as it stands now**, optional `?status=申請中` |
| GET | `/api/leave-requests/{record_id}` | One request by 管理ID |
| GET | `/api/payroll-items` | The payroll queue **as it stands now**, optional `?status=未処理` |
| GET | `/api/payroll-items/{record_id}` | One item by 管理ID |
| GET | `/api/policy/leave` · `/api/policy/payroll` | Prototype policy + its `_meta` honesty block |
| POST | `/api/automation/{workflow}/{record_id}/start` | Run one record of **either** workflow; `?run_execution=false` stops after the decision |
| GET | `/api/automation/history` | Every job this process has run, newest first |
| GET | `/api/automation/{job_id}` | One job: decision, execution, state history |
| POST | `/api/automation/{job_id}/human-decision` | Resolve an escalated job and carry the determination out |
| POST | `/api/demo/reset` | Restore the HR system and clear jobs, so the demo re-runs |
| GET | `/mock-hr/leave-applications` · `/mock-hr/payroll-items` | The mock HR application (HTML) |

## The mock internal HR application

A separate, server-rendered web app at `/mock-hr`, with its own mutable store. It
is the executor's target: "approve this request" means navigating and clicking in a
system the platform does not own, and "verify it worked" means independently
re-reading that system afterwards.

Both screens mirror what was directly observed in the Dataset B screenshots
(`phase2_dataset_b/visual_audit.md`):

| Screen | Fields | Reference note | Controls |
|---|---|---|---|
| `/leave-applications` | 管理ID / 社員ID / 氏名 / 申請種別 / 期間 / 所属部署 / ステータス | 事前承認要否 | 承認 · 差戻し |
| `/payroll-items` | 管理ID / 社員ID / 氏名 / 区分 / 金額 / ステータス | 申請者区分 · 承認権限 | 登録確定 · 保留 |

**Every interactive element carries a `data-testid`** — that is the contract with
the executor, which locates elements by test id and never by coordinates, position,
or translatable text. The ids the app renders are declared in
`execution/screens.py`; if the two drift apart, the browser tests fail loudly.

## The three kinds of truth

The prototype keeps these strictly separate, because Phase 2's visual audit showed
mechanical labels and screen-visible fields are not equally trustworthy:

1. **Dataset B evidence** — what was actually observed. One record
   (`P2-07048822-006`) has its full detail panel *and* the operator action
   confirmed by screenshot; six more were only seen as list rows, so their
   detail-only fields are `null` (**unknown**, not guessed).
2. **Prototype/demo records** — fabricated to exercise code paths, always
   `DEMO-`-prefixed so they can never be mistaken for observed ids.
3. **Prototype policy** (`data/policies.json`) — hand-authored rules. The
   operation logs never revealed the company's real approval policy, only that an
   action was taken. Nothing here was learned from the logs.

Four places where real evidence shaped behaviour rather than decorating it:

- **Neither workflow's negative action is automatic.** `allow_auto_rejection: false`
  (leave 差戻し) and `allow_auto_hold: false` (payroll 保留) — both controls exist on
  screen, neither was **ever** observed being used. They can only reach the browser
  through the human-review path.
- `allowed_request_types` contains only the three types actually observed being
  approved; 年次有給休暇 was seen in a list but never approved, so it escalates.
  `allowed_categories` follows the same rule, and excludes the salary-structure
  categories (役職手当廃止 / 役職手当新設) that change standing pay.
- `prior_approval_obtained` is a **prototype-only field**. Dataset B's UI showed
  whether prior approval was *required*, never whether it was *obtained*, so the
  one grounded leave record escalates instead of being decided either way.
- **The payroll amount limit is calibrated against the evidence, not invented in a
  vacuum.** Dataset B never revealed the real thresholds, so a value had to be
  chosen — and it is set *above* the one confirmation actually observed
  (`P1-07046967-001`, ¥25,213). Any lower value would make the agent escalate an
  item a human was directly seen confirming. That record is consequently the one
  case in the whole prototype where auto-execution **reproduces an observed human
  action end to end.**

## Layout

```
backend/
├── main.py                  FastAPI app: reference data + automation endpoints
├── orchestrator.py          drives one job through the state machine
├── repository.py            JSON loading + validation, cached (seed data)
├── pytest.ini
├── agent/                   ── the decision layer
│   ├── policy_engine.py     deterministic gates -> PolicyCheck[]   (no LLM)
│   ├── schemas.py           LlmDecisionDraft: the narrow output the model may return
│   ├── decision_agent.py    PydanticAI + Groq (openai/gpt-oss-20b)
│   └── guards.py            escalation-only invariants              (no LLM)
├── execution/               ── deterministic execution
│   ├── screens.py              per-workflow ScreenSpec (route + test ids) as DATA
│   ├── playwright_executor.py  ONE browser driver, data-testid selectors only
│   ├── verification.py         independent re-read of the record
│   └── runner.py               assembles ExecutionResult
├── mockhr/                  ── the browser target
│   ├── router.py            server-rendered HR screens (leave + payroll)
│   ├── store.py             one generic RecordStore, two queues + action log
│   └── templates/
├── models/                  Pydantic schemas
│   ├── common.py            shared enums incl. Provenance
│   ├── leave.py             LeaveRequest
│   ├── payroll.py           PayrollItem (workflow #2, declared only)
│   ├── agent.py             AgentDecision, PolicyCheck
│   ├── execution.py         ExecutionResult, ExecutionStep
│   └── job.py               AutomationJob, HumanDecision
├── state/machine.py         JobState enum, legal transitions, decision routing
├── workflows/
│   ├── base.py              declarative WorkflowDefinition types
│   ├── registry.py          workflow -> definition + record type + gates + loader
│   ├── leave_approval.py    workflow #1 definition
│   └── payroll_confirmation.py  workflow #2 definition
├── data/
│   ├── leave_requests.json  17 demo records (1 observed, 6 list-observed, 10 synthetic)
│   ├── payroll_items.json   11 demo records (1 observed, 2 list-observed, 8 synthetic)
│   └── policies.json        both explicit prototype policies
└── tests/                   64 tests, incl. real-browser runs
```

## Key invariants

**state ≠ decision.** `JobState` (where the job is: `POLICY_CHECK` → `EXECUTING` →
`VERIFYING` → `COMPLETED`) and `DecisionType` (what was concluded:
`APPROVE`/`REJECT`/`REVIEW`) are independent axes. A job can be in state
`EXECUTING` carrying decision `APPROVE`. `state/machine.py` rejects illegal moves
loudly via `assert_transition`.

**A check that could not be evaluated is not a check that failed.**
`PolicyCheck.passed` is three-valued: `True` / `False` / `None`. `None` means the
fact the rule needs is genuinely unknown, and it escalates rather than being
resolved in either direction.

**Clicking successfully is not the same as the record being approved.**
`ExecutionResult.success` (did the steps run?) and `verification_status` (did the
record actually change?) are separate fields. A run with `success=True,
verification_status=FAILED` is reported as a failure, and the job ends `FAILED`.

**The human's determination never overwrites the agent's.** `job.decision` and
`job.human_decision` coexist, so the audit trail keeps the interesting cases — the
ones where a person disagreed with the policy layer.

## Known limitations

- **Jobs are in memory.** Restarting the backend clears the audit trail. Persisting
  it properly is a database decision, not a demo decision.
- **One browser at a time.** The executor holds a process-wide lock, because
  concurrent runs against one shared HR system would interleave clicks and make
  verification meaningless.
- **`VERIFICATION_FAILED` is not a job state.** It is
  `state=FAILED` plus `execution.verification_status=FAILED`, which keeps the
  "clicked fine but nothing changed" case distinguishable from a crash without
  adding a second failure axis to the state machine.
- **The post-action status labels (承認済み / 差戻し) were never observed.** No
  approved or returned record was captured in any inspected Dataset B segment, only
  the button labels. They live in `WorkflowDefinition.verification`, are flagged
  there as a prototype assumption, and are configurable.
- **Two workflows, out of sixteen candidate process families.** Phase 2 found 16;
  these are the two with visually confirmed clean executions. The registry makes a
  third additive, but nothing beyond these two has been built or validated.
- **The payroll amount limit is a demonstration value.** Dataset B's 参照 note showed
  approval authority varies by requester type without ever showing the thresholds.
  Production use requires the client's real approval matrix.
- **Payroll figures cover port 5132 only.** Dataset B also shows payroll-items work
  on ports 5133 (7 executions) and 5134 (15) — 61 observed payroll executions in
  total — which this prototype does not cover.
