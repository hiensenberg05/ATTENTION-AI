# Deliverables

The four things the assignment asks for, in one place.

| # | Deliverable | Where | Status |
|---|---|---|---|
| 1 | Step 1 output — `segments.jsonl` | [`segments.jsonl`](segments.jsonl) | ✅ **Done** — 226 segments, all 15 Dataset B sessions |
| 2 | Full repository, with Git history | the repo itself | ✅ **Done** — see [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) |
| 3 | Final report | [`FINAL_REPORT.md`](FINAL_REPORT.md) | ⬜ **Not written yet** — scaffold only |
| 4 | Work log | [`WORKLOG.md`](WORKLOG.md) | ✅ **Done** — dated entries, incl. how generative AI was used |

---

## 1 — `segments.jsonl`

One JSON object per line, exactly the four required keys:

```json
{"session_id": "...", "start": "...Z", "end": "...Z", "label": "..."}
```

| | |
|---|---|
| Segments | 226 |
| Sessions covered | 15 / 15 Dataset B sessions |
| Distinct labels | 21 |
| Schema | 4 keys on every row, no missing, no extra |
| Timestamps | ISO 8601, UTC, `Z`-suffixed |
| md5 | `54efb1b5cc95f7a890b1fe46724b0b6d` |

**This file is not a copy.** `phase2/src/phase2_process_summary.py` writes this path
and `phase2/results/segments.jsonl` from the same string in the same function, so
the submitted file cannot silently fall behind a rerun. Regenerate with:

```powershell
python phase2\src\phase2_process_summary.py
```

**On the labels.** `label` is a deterministic process-family identifier derived
mechanically from the dominant application, or for browser work the host:port plus
the first hash-route segment — `B-127.0.0.1_5132_payroll-items`, not an invented
business name like `expense_processing`. The brief says the label text is not
evaluated, only that the same process consistently receives the same label, and a
mechanical identifier is the honest way to guarantee that: it is reproducible from
the data rather than assigned by judgement. What each label actually corresponds to
is documented in [`phase2/results/process_summary.csv`](../phase2/results/process_summary.csv).

**Read before trusting the counts.** Only 30.5% of recovered segments are "clean"
(single app, single browser route); the rest merge multiple business contexts into
one segment. Boundaries are therefore approximate and segment counts likely
*under*count true process executions. This is quantified honestly in
[`phase2/results/phase2_summary.md`](../phase2/results/phase2_summary.md) §7.

## 2 — Repository and Git history

The brief says *"we review how the work progressed"*, so the history is part of the
submission rather than incidental to it. It has not been squashed or rewritten, and
it shows the real shape of the work — including the audit that ended the first
attempt at Phase 1 ([`PHASE_HANDOFF_AUDIT.md`](../PHASE_HANDOFF_AUDIT.md)) and the
rewrite that followed.

Repository map: [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md).

## 3 — Final report

**Not written.** [`FINAL_REPORT.md`](FINAL_REPORT.md) currently holds the required
section structure, what evidence already exists for each, and what still has to be
written from scratch.

## 4 — Work log

[`WORKLOG.md`](WORKLOG.md) — dated entries covering what was tried, what was
measured, and what did not work. The brief also asks for a record of how
generative AI was used; that is recorded inline in the entries rather than in a
separate section, because the AI usage was the working method, not a footnote to it.

---

## Supporting evidence (not deliverables, but what the report cites)

| File | What it is |
|---|---|
| [`phase2/results/phase2_summary.md`](../phase2/results/phase2_summary.md) | The Step 2 analysis in full — process types, variants, automation shortlist, and §7's data-quality limits |
| [`phase2/results/automation_candidates.csv`](../phase2/results/automation_candidates.csv) | Impact / repeatability / feasibility / evidence / risk tiers per candidate |
| [`phase2/results/step3_prototype_spec.md`](../phase2/results/step3_prototype_spec.md) | The 17-point spec the Step 3 prototype was built against, both workflows |
| [`phase2/results/visual_audit.md`](../phase2/results/visual_audit.md) | Frame-by-frame screen audit confirming the routes are the business systems the labels claim |
| [`prototype_metrics.json`](../prototype_metrics.json) | The five prototype metrics, measured from real runs |
| [`phase1/README.md`](../phase1/README.md) | What each Phase 1 script answered, and why the approach changed |
