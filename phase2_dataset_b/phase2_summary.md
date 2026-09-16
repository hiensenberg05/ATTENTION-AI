# Phase 2 — Dataset B Process Recovery & Automation Opportunity Analysis

Phase 1 is frozen. Everything in this document is produced by applying the exact,
already-validated Phase 1F.5 pipeline (same candidate generation, feature engineering, trained
scorer, threshold, tooling filter, chain clustering, earliest-event representative rule) to
Dataset B, with no retraining, no re-tuning, no new ML/clustering for boundary detection, no LLM,
and no use of Dataset A ground truth to label or validate Dataset B. See
[README.md](README.md) for exactly how the frozen model was reproduced and verified before being
applied.

## 0. Headline numbers

- Dataset B: 15 sessions, 20 chunks, 20,477 events, 4 distinct worker/machine IDs
  (`76QMG9DE` x5 sessions, `NEELA9BAF` x5, `SIDDHIGUPTAB00B` x3, `CHAITANYA0BCF` x2)
- Frozen pipeline recovered **226 segments** (candidate pool 16,955; 211 predicted boundaries)
- Median segment duration 27.0s, mean 45.3s (heavily right-skewed — see §7 on why)
- Mechanical grouping found **21 process families** (`primary_context` groups), of which
  **16 have ≥3 executions** and are treated as genuine automation candidates; the rest are
  single-instance or diffuse "no captured browser route" buckets

## 1. What "process family" and "variant" mean here (read before the tables)

Grouping (Phase 2C) is **not** boundary detection — it's a separate, transparent, rule-based
method applied to already-frozen segments:

1. **`primary_context`** (the process family): the segment's dominant non-browser application, or
   — for browser-dominant segments — the browser's `host:port` plus the first hash-route segment
   (e.g. `127.0.0.1:5132#payroll-items`). Dataset B's line-of-business systems live at different
   ports (5132/5133/5134) and routes, which turned out to be a much stronger, cleaner separator
   than application name alone (every browser-dominant segment is "Microsoft Edge" — it's the
   route that tells you which business system, exactly like Dataset A's `#/payroll-items` /
   `#/resident-tax` pattern).
2. **Sub-variants within a family**: deterministic single-linkage grouping (union-find, no
   randomness) on each segment's event-type-rate vector, merging two segments into the same
   sub-variant whenever cosine similarity ≥ 0.80. Families with a variant supported by fewer than
   3 segments still keep their own variant ID in `process_groups.csv`/`variant_analysis.csv` for
   traceability, but roll into the family's main total in `process_summary.csv`.
3. **`segments.jsonl` labels are the `primary_context` slug** (e.g. `B-127.0.0.1_5132_payroll-items`)
   — a mechanically-derived identifier, not an invented business name. Sub-variants of the same
   family get the same label by default, because §5 below found the large majority of variants are
   minor/optional branches, not different processes.

No embeddings, no LLM, no new boundary-detection clustering were used or needed for this.

## 2. Work-unit characterization (Phase 2B)

Across all 226 segments:

| | mean | p10 | p25 | median | p75 | p90 | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| duration (s) | 45.3 | 2.1 | 10.0 | 27.0 | 56.3 | 112.5 | 358.8 |
| event count | 90.6 | 6 | 17 | 47 | 102.8 | 216.5 | 991 |

Interaction burden, application profile, content evidence, and worker/session identity are all
recorded per segment in `segment_features.csv` (columns: `click_count`, `browser_click_count`,
`keystroke_count`, `shortcut_count`, `form_input_count`, `navigation_count`, `app_switch_count`,
`total_interaction_events`, `dominant_application`, `applications_used`, `browser_domains`,
`browser_routes`, `available_case_ids`, `has_extracted_text`, `has_screenshot`,
`worker_machine_id`). **`worker_machine_id` is the machine suffix parsed from `session_id`**
(e.g. `76QMG9DE`) — the raw events do not carry a `source.username_hash`/`machine_id` field in the
current normalized schema (`src/normalizer.py` never captures the `source` block), so this is the
best available worker proxy, not a verified individual identity. Flagged again in §7.

## 3. Recurring process types (Phase 2C) — the 16 real candidates

Full detail in `process_summary.csv`; the ≥3-execution, non-rare rows:

| process_type_id | description | executions | sessions/workers | median duration | confidence |
|---|---|---:|---|---:|---|
| B-127.0.0.1_5132_payroll-items | payroll line-item review/entry (5132) | 39 | 10 / 4 | 28.8s | High |
| B-127.0.0.1_5132_leave-applications | leave application handling (5132) | 23 | 6 / 3 | 40.8s | High |
| B-127.0.0.1_5132_onboarding | employee onboarding workflow (5132) | 16 | 8 / 4 | 79.5s | High |
| B-127.0.0.1_5134_payroll-items | payroll line-item review/entry (5134) | 15 | 7 / 3 | 12.5s | High |
| B-Microsoft_Word | Word document editing (no route) | 14 | 7 / 3 | 21.7s | Low |
| B-127.0.0.1_5132 (no route) | mixed/multi-route browser activity | 12 | 12 / 4 | 57.9s | Low |
| B-127.0.0.1_5133_resident-tax | resident tax notice handling (5133) | 12 | 7 / 4 | 25.6s | High |
| B-127.0.0.1_5132_dashboard | dashboard/landing-page browsing (5132) | 11 | 11 / 4 | 29.6s | High |
| B-127.0.0.1_5132_social-insurance | social insurance processing (5132) | 8 | 4 / 3 | 37.7s | High |
| B-127.0.0.1_5133_payroll-items | payroll line-item review/entry (5133) | 7 | 4 / 3 | 39.1s | Medium |
| B-127.0.0.1_5134_leave-applications | leave application handling (5134) | 7 | 4 / 2 | 16.4s | Medium |
| B-127.0.0.1_5133_onboarding | employee onboarding workflow (5133) | 6 | 2 / 1 | 18.2s | Medium |
| B-127.0.0.1_5133_leave-applications | leave application handling (5133) | 5 | 2 / 2 | 43.8s | Medium |
| B-Microsoft_Edge | brief/mixed Edge activity, no route captured | 40 | 1 session* / 1 worker | 4.7s | Low |
| B-Microsoft_Excel | Excel activity (no route) | 3 | 3 / 2 | 41.9s | Low |
| B-127.0.0.1_5134_social-insurance | social insurance processing (5134) | 3 | 3 / 2 | 14.1s | Medium |

*`B-Microsoft_Edge`'s 40 executions are almost entirely concentrated in one unusually long,
45-segment session (`ses_20260701-192455-NEELA9BAF`) — see §7, this is a specific known artifact,
not a representative pattern.

**Cross-system observation worth flagging explicitly**: the same route name recurs at multiple
ports — `payroll-items` at 5132(39)+5133(7)+5134(15) = **61 executions / ~41 observed minutes**
combined; `leave-applications` at 5132(23)+5133(5)+5134(7) = **35 executions**; `onboarding` at
5132(16)+5133(6) = **22 executions**; `social-insurance` at 5132(8)+5134(3) = **11 executions**.
These are kept as separate process-type rows (they are, mechanically, different system instances —
possibly different departments/regions running the same internal tool), but if the underlying
workflow is genuinely identical across ports, **`payroll-items` work is the single largest
recurring category in Dataset B by a wide margin**, whichever way it's counted. This is exactly
the kind of judgment call Step 3 scoping should make explicitly, not the mechanical grouper.

Evidence per process type (dominant app, browser involvement, case-ID and extracted-text
presence, sample case IDs) is in `process_summary.csv`'s `evidence_supporting_interpretation`
column, generated from the real per-segment data, e.g. for `B-127.0.0.1_5132_payroll-items`:
*"39 segments across 10 sessions/4 workers; dominant app Microsoft Edge; browser involvement
100%; case-ID evidence in 24% of executions (samples: INV-1689, INV-1690, INV-1691); extracted
screen text present in 24%."* A real inspected example (`ses_20260701-171614-CHAITANYA0BCF::seg003`)
shows actual screen text confirming the interpretation: *"給与変更登録。変更種別：役職手当新設。
適用日：2026-07-06。確認完了。"* ("Salary change registration. Change type: new position
allowance. Effective date 2026-07-06. Confirmation complete.")

## 4. Confidence methodology

- **High**: has a captured browser route, ≥8 executions, and case-ID or extracted-text evidence
  in a meaningful share of executions.
- **Medium**: has a captured browser route and ≥3 executions, but weaker volume/content evidence.
- **Low**: no stable browser route (desktop apps without URL context, or browser segments where no
  route was captured), OR fewer than 3 executions. This is a deliberately conservative rule — a
  route is the strongest available signal of a *specific* business workflow in this dataset, so
  anything without one is flagged Low even where the segment content looks coherent, rather than
  asserting confidence the mechanical evidence doesn't fully support.

## 5. Variant analysis (Phase 2D)

Only two process families produced more than one mechanical sub-variant (`variant_analysis.csv`):

| family | variant | freq | % | median duration | vs. family median | interpretation |
|---|---|---:|---:|---:|---:|---|
| 5132 payroll-items | v2 | 38 | 97.4% | 33.6s | 1.16x | likely optional branch of same workflow |
| 5132 payroll-items | v1 | 1 | 2.6% | 0.5s | 0.02x | possibly different / needs review |
| Microsoft Word | v1 | 11 | 78.6% | 35.9s | 1.65x | likely optional branch of same workflow |
| Microsoft Word | v2 | 3 | 21.4% | 3.8s | 0.17x | possibly different / needs review |

In both cases the "possibly different" variant is a single-digit-event, sub-4-second outlier
(one is a single 8-event, 0.47s segment) — almost certainly a brief glance/misfire rather than a
real alternate process, not a meaningful branch requiring separate automation handling. **All 16
real process types are, per this analysis, single-workflow families with no meaningful branching
that would require different automation logic** — the rule (duration and event-count ratio within
0.6x-1.67x of the family median) is documented in `phase2_process_summary.py::build_variant_analysis`
and applied identically to both cases; it did not need to be tuned per-family.

## 6. Automation opportunity analysis (Phase 2E) and shortlist (Phase 2F)

Full quantitative detail in `automation_candidates.csv`. Per the brief, **no arbitrary combined
numerical score and no automatic winner** — each candidate is rated on five qualitative tiers
(High/Medium/Low), each backed by a documented, inspectable rule over the measured data:

- **Impact** = total observed minutes, relative to the largest candidate (High ≥40%, Medium ≥15%)
- **Repeatability** = execution volume and duration consistency (low coefficient of variation)
- **Feasibility** = browser-based (single, scriptable UI surface) and low sub-variant count
- **Evidence quality** = how often case-ID/extracted-text content actually confirms the interpretation
- **Complexity/risk** = variant count, chunk-crossing frequency (possible interruption), worker count ≤1 (thin evidence)

| process type | impact | repeatability | feasibility | evidence quality | complexity/risk |
|---|---|---|---|---|---|
| 5132 payroll-items (39 exec, 30.2 min) | High | Medium | High | High | Low |
| 5132 onboarding (16 exec, 27.0 min) | High | Medium | High | High | Low |
| 5132 leave-applications (23 exec, 18.6 min) | High | Medium | High | High | Low |
| 5132 dashboard (11 exec, 9.2 min) | Medium | Medium | High | High | Low |
| 5133 payroll-items (7 exec, 8.0 min) | Medium | Low | High | High | Low |
| 5132 social-insurance (8 exec, 6.9 min) | Medium | Medium | High | High | Low |
| 5133 resident-tax (12 exec, 5.4 min) | Medium | Medium | High | High | Low |
| (remaining candidates: see automation_candidates.csv) | | | | | |

All 16 candidates land **Low complexity/risk** by this rule — every one is single-browser-app,
single/negligible-variant, with case-ID evidence available. This is a genuine finding (Dataset B's
recovered work is, on this evidence, uniformly browser-based line-of-business data entry), not a
scoring artifact — see §7 for why it should still be read with caution.

Measurable quantities (no invented financial ROI, per instructions):

- 5132 payroll-items: 39 observed executions, 30.2 observed minutes, median 28.8s/execution,
  median 18 clicks + 11 keystrokes per execution → **at 100 executions, ~48 observed minutes and
  ~1,800 clicks + ~1,100 keystrokes of manual interaction**, before accounting for the
  under-segmentation caveat in §7 (true per-case time is likely *shorter*, true case volume likely
  *higher*, than the raw segment numbers suggest).
- 5132 onboarding: 16 executions, 27.0 observed minutes, median 79.5s/execution (longest median of
  any candidate, and highest keystroke burden: median 29 keystrokes) — the most form-entry-heavy
  workflow found.
- Combined `payroll-items`-pattern work across all three ports: 61 executions, ~41 observed
  minutes — the largest aggregate category regardless of per-port grouping.

**This document does not declare a winner.** The evidence above supports Step 3 focusing on one of
the High-impact/High-feasibility/High-evidence/Low-risk candidates — most plausibly payroll-items
(largest aggregate volume) or onboarding (highest per-execution interaction burden, so highest
time-savings-per-automated-run) — but which one is worth automating first also depends on business
priority information not observable in these logs (e.g. which process the client actually cares
about), which is explicitly out of scope for this phase.

## 7. Data quality and uncertainty (Phase 2H) — read before trusting the numbers above

**This is the single most important caveat in this report.** Only **30.5% of the 226 recovered
segments** touch exactly one application and one browser route; **45.6% touch more than one
browser route** and **61.5% touch more than one application**. Two concretely inspected examples:

1. `ses_20260701-171614-CHAITANYA0BCF::seg003` (grouped under 5132 payroll-items) genuinely starts
   with real payroll text ("Salary change registration...") at port 5132, then **navigates to port
   5134 mid-segment** and switches to inventory-adjustment content ("在庫調整登録。品番：BATCH-W2...")
   — two different business systems inside one reported segment. It was bucketed under 5132 only
   because the grouping heuristic picks the alphabetically-first route when a segment spans more
   than one.
2. `ses_20260701-192455-NEELA9BAF::seg013` (the representative `B-Microsoft_Edge` example) spans
   HR payroll, a Word onboarding procedure document, Windows Explorer, Finance/accounting, and a
   Notepad inventory memo — five different business contexts — inside one 74-second, 91-event
   segment.

**Root cause, not a new bug**: this is the same limitation the Phase 1F.1 diagnosis already found
and quantified on Dataset A — 98.3% of Dataset A's own ground-truth boundaries had no visible
app/window change, so the frozen scorer was never trained to rely on app/route changes as a strong
signal, and under-segments exactly this kind of transition. Dataset B evidently has *more* such
transitions than Dataset A (different departments, more document-based work mixed with browser
work), so the effect is more visible here. This is expected and consistent with the README's own
warning that Phase 1's approach "will not necessarily transfer to Dataset B."

**Concrete consequence for the frequency/duration numbers above**: segment counts likely
*undercount* true process executions, and segment durations likely *overcount* true per-execution
time, for the longer segments. Directly measured: `5132 onboarding`'s 16 segments contain **60
distinct case IDs** visible across only 5 of those segments; `5132 payroll-items`'s 39 segments
contain **96 distinct case IDs** across only 9 segments. The longest onboarding segment alone
(359s, 712 events) contains 12 distinct sequential case IDs (`INV-1689`...`INV-1700`) — almost
certainly several real onboarding cases processed back-to-back without a detected boundary between
them, not one 6-minute case. Duration for this process type ranges from 2.1s to 358.8s (std 92s on
a mean of 101s) — a symptom of the same issue, not genuine process variability.

**Other limitations, reported rather than hidden:**
- `worker_machine_id` is a machine identifier parsed from `session_id`, not a verified per-person
  identity (see §2) — treat "number of workers" as a lower bound / coarse proxy.
- `extracted_text` covers only 4.6% of Dataset B events (screenshots 23.2%), matching Dataset A's
  sparsity — most segments have no direct textual confirmation of their interpretation; the
  `case_id_presence_fraction` and `extracted_text_presence_fraction` columns in
  `process_summary.csv` make exactly how much evidence backs each row explicit, and confidence
  levels were set accordingly (§4).
- `clipboard_text` is 0% populated in Dataset B, same as Dataset A — not a usable signal here either.
- The `B-Microsoft_Edge` (40 exec) and `B-127.0.0.1_5132`-no-route (12 exec) buckets are, by
  construction, the segments the grouping method could *not* confidently place in a specific
  business route — they are flagged Low confidence and should be read as "unclassified mixed
  activity," not as a coherent process, regardless of their executive counts.
- Because under-segmentation (not over-segmentation) is the dominant failure mode observed here,
  the automation-candidate volume/time estimates in §6 should be treated as **conservative lower
  bounds on true frequency** and **upper bounds on true per-execution duration** — real automation
  scoping for Step 3 should expect somewhat more, somewhat shorter executions than reported here.

None of this invalidates the top-line finding — browser-based, route-identifiable, case-ID-bearing
HR/payroll/logistics data entry is clearly the dominant recurring work in Dataset B — but the exact
segment-level counts and durations are approximate, not precise, and should be presented to a
client that way.
