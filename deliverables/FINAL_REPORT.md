# Final Report — *not yet written*

> **Status: scaffold.** This file exists so the deliverable has a home and a plan.
> It is an outline plus an inventory of evidence, not the report. Nothing below
> should be submitted as-is.

The brief names five things the report must explain (`README.md` → Deliverables → 3).
They are reproduced verbatim as the section headings, so none can be quietly dropped.

---

## 1. Step 2 analysis, the prioritized automation candidates, and the reasoning

**Material that already exists:**

- [`phase2/results/phase2_summary.md`](../phase2/results/phase2_summary.md) — the full
  analysis. §6 is the automation opportunity analysis and shortlist; §7 is the
  data-quality limits.
- [`phase2/results/automation_candidates.csv`](../phase2/results/automation_candidates.csv) —
  per-candidate impact / repeatability / feasibility / evidence / risk tiers, with
  execution counts, observed minutes, worker counts and case-ID samples.
- [`phase2/results/process_summary.csv`](../phase2/results/process_summary.csv),
  [`variant_analysis.csv`](../phase2/results/variant_analysis.csv),
  [`representative_segments.csv`](../phase2/results/representative_segments.csv).
- Plots in [`phase2/results/plots/`](../phase2/results/plots/).

**What has to be written from scratch:**

> ⚠️ **Gap.** Phase 2 produced *tiers* and a shortlist, and deliberately declared no
> winner — that was correct for that phase, which was instructed not to. The report
> is asked for candidates **in priority order**, which is a different claim and does
> not exist anywhere yet. It needs to be stated as a ranking with the reasoning, and
> it must confront the honest problem Phase 2 already recorded: true business
> priority is not observable in these logs. The ranking therefore has to be explicit
> about what it *is* ordered on (observed volume, time, worker spread, evidence
> strength, feasibility) and what it cannot see.

---

## 2. What was built in Step 3 — and **why that process and scope**, and **why that implementation form**

**Material that already exists:**

- [`phase2/results/step3_prototype_spec.md`](../phase2/results/step3_prototype_spec.md) —
  the 17-point spec for both workflows, including point 12 (what can be automated)
  and point 13 (what must stay human-in-the-loop).
- [`backend/README.md`](../backend/README.md) — the architecture as built.
- [`frontend/README.md`](../frontend/README.md) — the operator console.
- Why *these two* processes: payroll-items is the highest-volume candidate
  (39 executions, 30.16 observed minutes, 4 workers) and leave-applications is the
  one with a screenshot-confirmed detail screen (23 executions, 18.63 minutes,
  3 workers). Both are in `automation_candidates.csv` with `confidence_level: High`.

**What has to be written from scratch:**

> ⚠️ **Gap — the biggest one.** *"Why that implementation form"* is a named,
> explicitly required point, and there is **no material for it anywhere in the repo**.
> The brief itself names the alternatives that have to be addressed: n8n, Power
> Automate, a deterministic script, a desktop application. The report has to say why
> each was rejected for this problem, not merely why the chosen form is good.
>
> The chosen form was: an LLM that reads an explicit policy and returns a structured
> decision, Python that routes the job through a state machine, Playwright that
> performs the decided action against the real screens, and an independent re-read
> that verifies the record actually changed — *"AI decides. Python controls.
> Playwright executes. Verification proves the result."* The argument for it over the
> alternatives is real but has never been written down.

---

## 3. What manual work remains after deployment, and the impact realistically expected

**Material that already exists:**

- [`prototype_metrics.json`](../prototype_metrics.json) — measured, not estimated:
  26 runs, 10 reaching the browser, **100% verified (10/10)**, **30.8% automated /
  69.2% escalated to human review**, prototype median **1.32s**.
- Per-workflow split: payroll automates 40%, leave 25% — and the reason is recorded.
  The payroll 参照 policy note was readable on the one record whose detail panel an
  operator actually opened; leave's `prior_approval_obtained` was never visible on
  any record. **Automatability here is bounded by which fields the operator's screen
  happened to expose, not by how hard the task is.** That is the honest ROI finding
  and it should lead this section.
- `step3_prototype_spec.md` point 13 — what must stay human.
- The escalation rate is a *designed* outcome, not a failure. Say so explicitly.

**What has to be written from scratch:**

> ⚠️ **Caution, not a gap.** There is a strong temptation to state a savings figure
> by subtracting prototype latency from the human baseline. The prototype refuses to
> do this on screen and the report must refuse too: prototype latency is browser time
> against a local mock, while the Dataset B figures are human time in a test
> environment whose waits were deliberately shortened. They are not comparable
> populations. Savings extrapolated from 226 segments — 69.5% of which are merged
> multi-case sessions — would not survive scrutiny.

---

## 4. Anticipated implementation and rollout risks, **with your mitigation approach**

**Material that already exists — the risks are unusually well documented:**

- Only **30.5% of segments are clean**; the rest merge business contexts
  (`phase2_summary.md` §7).
- Route names are not business labels — the mapping was confirmed by screen audit
  ([`visual_audit.md`](../phase2/results/visual_audit.md)), not assumed.
- The post-action labels 承認済み / 差戻し were **never observed** in Dataset B.
- The target is a mock HR application built to match the screenshots, not the real
  system.
- Auto-approval evidence rests on a small number of observed records.
- `step3_prototype_spec.md` point 14 (known exceptions/risks) and point 17
  (evidence strength and limitations).

**What has to be written from scratch:**

> ⚠️ **Gap.** The repo documents risks thoroughly and mitigations **not at all** —
> zero occurrences of "mitigat" outside the brief. The brief asks for risks *and how
> you would address them*. Each risk above needs a paired, concrete mitigation.
>
> Some already exist as *built behaviour* and merely need naming as mitigations: the
> guard that lets the model escalate but never de-escalate; the three-valued policy
> check where unknown escalates rather than silently passing; the independent
> re-read from the queue screen rather than the page that submitted the action; the
> `DEMO-` prefix on every synthetic record; the adversarial probe (28 records
> probed, 20 the policy wanted escalated, **20 held, 0 leaked**).

---

## 5. How the days were allocated, and why

**Resolved — this now lives in the work log.** [`WORKLOG.md`](WORKLOG.md) opens with
a *How the days were allocated* table: five days, 14–18 September, each with what it
covered and why it came in that order, plus the reasoning for the split (Phase 1 took
two and a half days because that is where the uncertainty was; Phase 3 took one
because Phase 2 had already specified it).

The brief lists this under the report rather than the work log, so the report should
still carry a short section — roughly half a page summarising the allocation and the
reasoning, ending with a pointer to the work log for the day-by-day detail. Duplicating
the full table in both places would just create two things to keep in sync.

Note the honest figure: the work took **five days, not seven**. The log presents it
that way rather than padding it out.

---

## Drafting notes

- All five sections can now be drafted from the repo.
- Three things still exist nowhere and are genuinely new writing: **why the
  alternatives were rejected** (§2 — a named requirement with zero supporting
  material, and the biggest gap), **risk mitigations** (§4 — the risks are
  documented thoroughly, the mitigations not at all), and **an explicit ranked
  ordering** of candidates (§1 — Phase 2 deliberately declared no winner).
- Two findings from day 5 belong in the report: the 1F variant/tolerance table
  (1F.5 is *worse* than 1F.4 at exact match — state it and own the trade-off), and
  the label-granularity decision in `segments.jsonl` (process, not server instance).
- Every figure quoted in the report should be traceable to a committed file, since
  the result tables are tracked precisely so a reviewer can check them.
