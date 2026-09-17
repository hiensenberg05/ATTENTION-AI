# Back-Office Automation Agent — backend

Step 3 prototype for the IMbesideYou FDE assignment. Separate from the Phase 1/2
analysis code (`src/`, `phase1*/`, `phase2_dataset_b/`), which is frozen and untouched.

**Stage: agent + executor live.** An LLM evaluates an explicit policy and returns a
structured decision, Python routes the job through a state machine, Playwright
performs the decided action in a mock HR system, and an independent re-read
verifies that the record actually changed.

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
- Mock HR system: <http://127.0.0.1:8000/mock-hr/leave-applications>

Tests (33, including real-browser runs against a real server): `python -m pytest`

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
| GET | `/api/workflows/{workflow}` | One workflow (404 for `PAYROLL_CONFIRMATION` — declared, not defined) |
| GET | `/api/leave-requests` | The HR queue **as it stands now**, optional `?status=申請中` |
| GET | `/api/leave-requests/{record_id}` | One request by 管理ID |
| GET | `/api/policy/leave` | Prototype policy + its `_meta` honesty block |
| POST | `/api/automation/leave/{record_id}/start` | Run one record through the pipeline; `?run_execution=false` stops after the decision |
| GET | `/api/automation/history` | Every job this process has run, newest first |
| GET | `/api/automation/{job_id}` | One job: decision, execution, state history |
| POST | `/api/automation/{job_id}/human-decision` | Resolve an escalated job and carry the determination out |
| POST | `/api/demo/reset` | Restore the HR system and clear jobs, so the demo re-runs |
| GET | `/mock-hr/leave-applications` | The mock HR application (HTML) |

## The mock internal HR application

A separate, server-rendered web app at `/mock-hr`, with its own mutable store. It
is the executor's target: "approve this request" means navigating and clicking in a
system the platform does not own, and "verify it worked" means independently
re-reading that system afterwards.

Its field layout mirrors what was directly observed in the Dataset B screenshots
(`phase2_dataset_b/visual_audit.md`). **Every interactive element carries a
`data-testid`** — that is the contract with the executor, which locates elements by
test id and never by coordinates, position, or translatable text.

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

Three places where real evidence shaped behaviour rather than decorating it:

- `allow_auto_rejection: false` — the 差戻し control exists but was **never**
  observed being used, so the platform never rejects automatically. A rejection
  can only ever reach the browser through the human-review path.
- `allowed_request_types` contains only the three types actually observed being
  approved; 年次有給休暇 was seen in a list but never approved, so it escalates.
- `prior_approval_obtained` is a **prototype-only field**. Dataset B's UI showed
  whether prior approval was *required*, never whether it was *obtained*, so the
  one grounded record escalates instead of being decided either way.

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
│   ├── playwright_executor.py  browser driver, data-testid selectors only
│   ├── verification.py         independent re-read of the record
│   └── runner.py               assembles ExecutionResult
├── mockhr/                  ── the browser target
│   ├── router.py            server-rendered HR screens
│   ├── store.py             mutable state + action log
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
│   └── leave_approval.py    workflow #1 definition
├── data/
│   ├── leave_requests.json  17 demo records (1 observed, 6 list-observed, 10 synthetic)
│   ├── payroll_items.json   4 records, prepared for workflow #2
│   └── policies.json        explicit prototype policy
└── tests/                   33 tests, incl. real-browser runs
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
- **Only Leave Approval is implemented.** Payroll Confirmation has demo data, an
  enum member and a draft policy section, but no workflow definition and no code
  path.
