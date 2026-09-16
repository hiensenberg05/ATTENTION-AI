# Phase 2 — Dataset B Process Recovery & Automation Opportunity Analysis

Applies the FROZEN Phase 1F.5 segmentation pipeline to Dataset B, then discovers recurring
process types and automation candidates from the recovered segments. Phase 1 was not modified,
retrained, or re-tuned in any way; Dataset A ground truth was never read for or applied to
Dataset B. Full narrative and evidence: **[phase2_summary.md](phase2_summary.md)**.

## Reproduce

```
.\venv\Scripts\python.exe src\phase2_dataset_b_segmentation.py   # ~2 min: reproduces the frozen 1F.5 fit on Dataset A, verifies it, applies it to Dataset B
.\venv\Scripts\python.exe src\phase2_process_analysis.py         # audit table + mechanical process-type grouping
.\venv\Scripts\python.exe src\phase2_process_summary.py          # summary/variants/automation candidates/representatives/plots/segments.jsonl
```

All three scripts are deterministic given the same input data — no randomness anywhere in Phase 2
(the frozen model itself has a fixed `random_state`; the grouping method is rule-based/single-linkage
with a fixed similarity threshold, not an iterative/randomized clustering algorithm).

## Why Phase 1F.5 was *reproduced* rather than just *reused*

`phase1f5_segmentation.py` never persisted its fitted model/threshold to disk — they only existed
inside that script's `main()`. `src/phase2_dataset_b_segmentation.py::fit_frozen_pipeline_on_dataset_a`
reruns the exact same deterministic fit procedure (same candidate generation, same features
including Phase 1F.3's tooling filter and Phase 1F.4's case-ID features, same held-out split, same
GroupKFold OOF threshold search, same LogisticRegression hyperparameters/`random_state=41`) on
Dataset A only, then `verify_frozen_reproduction()` checks the result against Phase 1F.5's own
recorded numbers (threshold 0.88, training OOF F1 0.3404874499818116) and **refuses to proceed** if
they don't match exactly. This ran clean on the actual execution — the frozen artifact is
genuinely reproduced, not approximated. The reproduced model and threshold are then applied to
Dataset B's own candidates, computed by the same frozen feature-engineering functions, with the
Dataset-A-derived event-type vocabulary frozen too (not recomputed from Dataset B).

## Files

| File | Contents |
|---|---|
| `segments.jsonl` | Required deliverable format: `{session_id, start, end, label}` per segment. `label` is a deterministic process-family identifier (e.g. `B-127.0.0.1_5132_payroll-items`), not an invented business name. |
| `segment_features.csv` | Full per-segment audit table: timestamps, event/interaction counts, applications, browser routes, case IDs, text/screenshot availability, chunk-crossing — everything needed to manually inspect any segment. |
| `process_groups.csv` | segment → process-family / sub-variant mapping. |
| `process_summary.csv` | Per process-family aggregate stats, evidence, and confidence level (Phase 2C). |
| `variant_analysis.csv` | Sub-variant breakdown within each process family, and whether each variant looks like a minor branch or a possibly-different process (Phase 2D). |
| `automation_candidates.csv` | Quantitative automation-opportunity metrics + qualitative Impact/Repeatability/Feasibility/Evidence/Risk tiers (Phase 2E/2F) — no combined score, no declared winner. |
| `representative_segments.csv` | 2-3 representative segments per process family (shortest/median/longest by duration) for manual verification. |
| `raw_segments.csv`, `candidate_scores.csv` | Intermediate Phase 2A output (raw segment boundaries, full scored candidate pool) — kept for traceability/debugging. |
| `phase2a_run_summary.json` | Frozen-fit verification + Dataset B run counts. |
| `plots/` | process frequency, total time by process, duration distribution, interaction burden, process/variant distribution. |
| `phase2_summary.md` | Full write-up: characterization, process types with evidence, variants, automation analysis/shortlist, representative examples, and — importantly — data quality/uncertainty. |

## Read this before trusting the numbers

`phase2_summary.md` §7 documents a real, quantified limitation: only 30.5% of recovered segments
are "clean" (single app, single browser route); the rest mix multiple business contexts inside one
segment, because Dataset B has more app/route-invisible transitions than Dataset A did and the
frozen scorer was never trained to catch those well (this is the same limitation the Phase 1F.1
diagnosis found and quantified on Dataset A itself, just more visible here). Segment counts likely
undercount true process executions for the longer, merged segments — concretely shown via distinct
case-ID counts inside single segments. This does not invalidate the top-line finding (browser-based
HR/payroll/logistics data entry is clearly Dataset B's dominant recurring work), but exact counts
and durations are approximate, not precise.

## Explicitly out of scope for this phase (per instructions)

No Step 3 prototype, no automation-candidate "winner" declared, no Phase 1 changes, no LLM, no new
segmentation/boundary-detection clustering, no Dataset A GT used for Dataset B labeling.
