# Phase 1E / 1F Handoff Audit

Scope: read-only inspection of the repository as handed off from Codex. No code was changed, no
pipeline was rewritten, and Dataset B was not touched. One attempt to *execute* the existing
`src/phase1f_segmentation.py` (to see whether it runs cleanly and to check why its outputs are
missing) was made and was interrupted/declined by the user before it produced any result — so
runtime behavior of Phase 1F is **not** verified in this audit; everything below about Phase 1F
correctness is from static code review only.

---

## Phase 1E

**Intended:** investigate whether the Phase 1D finding — `interaction_change` (adjacent
event-type differs) gives 97.5% boundary recall but fires on 65.5% of all transitions — could be
narrowed using run/burst-level consolidation instead of single-event change, to shrink the
candidate pool without losing recall.

**Actually implemented:** `src/phase1e_interaction_sequences.py` (8 lines). For each session it:
- builds run-length-encoded "runs" of consecutive identical `event_type`
- computes three signals: `single_change` (baseline, same as 1D's `interaction_change`),
  `run_boundary_change` (change only where both the previous and next run have length ≥2), and
  `burst_change` (change where either adjacent run has length ≥3)
- reports recall, candidate count, density, and false-positive rate for each, to
  `phase1e_interaction_sequences/sequence_signal_statistics.csv`, plus up to 1,000 example rows to
  `boundary_examples.csv`.

**Results found** (verified by re-reading the actual CSV, not just the README/WORKLOG prose):

| signal | recall | count | density | FP rate |
|---|---:|---:|---:|---:|
| single_change | 97.54% | 91,231 | 65.5% | 65.2% |
| run_boundary_change | 0.072% | 117 | 0.084% | 0.084% |
| burst_change | 15.77% | 10,281 | 7.39% | 7.30% |

These numbers match the table in the handoff prompt and WORKLOG exactly. Note this run used a
slightly different candidate pool definition than 1D (`e.event_type.ne(shift)` over the whole
session vs. 1D's per-session shift with the same logic) — they're effectively the same
computation, so the reported 97.5%/65.5% baseline is consistent across 1D and 1E.

**Correctness / issues:**
- No GT process identity, code, or variant is used — only `event_type` sequence and `execution_id`
  (used solely as the evaluation label `b`, never as a feature). No leakage.
- This is a pure diagnostic script (no model, no candidate generator output consumed downstream) —
  consistent with its README's own description ("no segmentation algorithm... implemented").
- The conclusion drawn ("simple run/burst consolidation is not sufficient, do not use it") is
  correctly supported by the numbers: `run_boundary_change` collapses recall to ~0%, and
  `burst_change` trades most of the recall away for a ~9x density reduction — neither is usable
  alone.
- **Reproducibility gap:** both output CSVs are excluded by `.gitignore` (`*.csv`) and are **not
  committed** — only the PNG plot is staged. Phase 1E has no commit at all (see below). If someone
  cloned the last real commit (`c661371`), Phase 1E would not exist and its numbers would be
  unverifiable without rerunning the script.

**Verdict: Phase 1E is correctly implemented and its conclusions are consistent with the
underlying data.** It is diagnostic-only, as intended, and appropriately used to *rule out* a
direction rather than to build a new candidate generator.

---

## Phase 1F

**Does it exist?** Yes — `src/phase1f_segmentation.py` (70 lines) and `phase1f_segmentation/README.md`
exist and describe a complete design. But:

**Was it ever run?** No. `phase1f_segmentation/` contains only `README.md` and an **empty**
`plots/` directory. None of the six output files the script itself writes
(`boundary_results.csv`, `segment_results.csv`, `calibration_curve.csv`,
`segmentation_statistics.csv`, `session_results.csv`, `scorer_feature_weights.csv`) exist
anywhere in the repo — I searched the full tree by filename, not just the phase folder. This is
exactly why you did not receive Phase 1F outputs: **there are none, anywhere, committed or
uncommitted.** WORKLOG.md's own Phase 1F entry says "pending final held-out results," which
matches.

**Git history:** Phase 1E and Phase 1F have **zero commits** touching them (`git log --all` on
both paths returns nothing). Both exist only as staged-but-uncommitted changes in the current
working tree. The last real commit is `c661371` ("docs: add candidate signal coverage
diagnosis" = Phase 1D). So from the repository's committed history, work stops at Phase 1D — 1E
and 1F are working-tree-only artifacts that were never checkpointed.

### What the code does (static read of `src/phase1f_segmentation.py`)

1. **Feature/label construction** (lines 39–41): loads `dataset_a_events_with_gt.parquet`,
   computes per-event `gap_seconds`, `interaction_change`, `app_change`, `window_change`,
   `browser_context_change`, `chunk_change`, and `true_boundary` (execution_id changes between
   adjacent events, both non-null). Candidate pool = interaction/app/window/browser-context change,
   OR gap > 1s, OR event type in `{clipboard_change, browser_navigation, browser_form_input}`.
   `chunk_change` is deliberately **excluded** from the candidate-trigger OR-clause (comment: "Chunks
   are never candidates alone") — consistent with the stated constraint that chunk boundaries must
   not be treated as process boundaries.
2. **Context features** (`features()`, lines 23–37): for each candidate, 20-event pre/post windows
   are summarized into gap stats, app/window/tab-switch rates, unique app/window/tab counts, text
   availability rate, keyboard/mouse/browser/clipboard activity mix, per-event-type rates (top-18
   vocabulary), and pre→post deltas of all of the above. This is genuine sequence/context
   representation, not a single-event rule — matches the intended architecture diagram.
3. **Train/held-out split** (line 42): every 5th sorted session_id is held out — same convention as
   Phase 1B. Threshold is chosen **only** from 5-fold `GroupKFold` (grouped by `session_id`)
   out-of-fold predictions on the **training** sessions (lines 44–49), sweeping 0.05–0.95 and
   picking the F1-maximizing threshold. The held-out sessions never influence threshold selection.
   The final model is then refit on all training sessions (line 50) and scored once on everything,
   including held-out, for evaluation.
4. **Post-processing** (`select()`, lines 15–19): greedy selection sorted by score descending, with
   a 3-event minimum-separation non-maximum-suppression — prevents the model from picking two cuts
   right next to each other.
5. **Segment construction** (lines 52–57): cuts partition each session's full (multi-chunk)
   timeline into contiguous segments; each segment records `crosses_chunk` and `handling`
   (`continuation_across_chunk` vs `within_chunk`), and `gt_execution_count` /
   `gt_primary_execution_id` for evaluation-only bookkeeping.
6. **Evaluation** (lines 58–63): precision/recall/F1 and segment stats computed separately for
   `heldout` and `all_dataset_a` scopes, plus per-session breakdown.
7. **Explainability** (lines 64–68): 20 examples per outcome bucket (TP/FP/FN_candidate/
   FN_not_candidate) with pre/post textual context, and top-20 |coefficient| feature weights from
   the logistic model.

### Leakage check

- The feature set `fs` (line 42) is every non-object column of the candidate frame **except**
  `{row_id, session_id, timestamp_iso, event_index, true_boundary, gt_execution_id}`. None of
  `process_code`, `process_name`, `family_name`, `variant`, `case_id`, `domain`, or any other GT
  identity/label column is present in the candidate feature frame at all (verified by reading
  `features()` — it only ever reads `event_type`, `gap_seconds`, `active_app`, `window_title`,
  `browser_tab_id`, `extracted_text`, `clipboard_text`, and the four change flags). `execution_id`
  is only read once, downstream of scoring, purely to populate `gt_execution_id` for CSV output
  and the `true_boundary` label — never fed to the model.
  **No GT process-identity leakage found.**
- `event_index` (a per-session running event count) **is** in the training feature set, despite
  being in a plausible position to be dropped alongside `row_id`. It's not a GT/label leak, but it
  is a somewhat arbitrary positional feature (later events in long sessions get higher values) that
  wasn't flagged or justified in the README. Minor design concern, not a correctness bug.
- `chunk_change` is used as a **soft scoring feature** even though it cannot trigger a candidate or
  force a cut directly. This is defensible (the README states the rationale explicitly) but is
  worth flagging: it means chunk-recording artifacts still influence the learned score, just not as
  a hard rule.
- Held-out/training separation is correctly respected throughout: `StandardScaler` and
  `LogisticRegression` are fit per-fold on training rows only (line 45), the threshold sweep uses
  only OOF predictions on training sessions (lines 46–49), and the refit-on-all-training model
  (line 50) is applied to held-out data only for final scoring, never for fitting. **No
  train/held-out leakage found in the code.**

### Special-case handling (continuation / split / suspend / resume / chunk)

- **Chunk crossing:** handled — segments spanning multiple chunks are explicitly flagged
  (`crosses_chunk`, `handling`), and the underlying event timeline already concatenates all chunks
  of a session (via `dataset_a_events_with_gt.parquet`, built across chunks in Phase 0), so
  segmentation naturally operates across chunk boundaries rather than being reset by them.
- **Suspend/resume/split:** **not modeled as a distinct case.** The README explicitly says this is
  intentional — "Suspend/resume and split behavior gets no GT-derived rule: it is retained only
  when the contextual score clears the selected threshold." In other words, 1F does not
  special-case these GT fields (`split_id`, `phase`, `continues_from_prev/next`) at all; a
  suspend/resume transition is only detected if the general contextual scorer happens to fire on
  it, exactly like any other boundary. This is a legitimate simplification, but it is a **deviation
  from the earlier Phase-1-initial recommendation** ("explicitly model GT continuation/split
  cases") and, since the pipeline was never run, there's no evidence yet of how well (or poorly) the
  generic scorer actually recovers these specific cases.
- **Missing-end GT executions:** correctly excluded upstream. `data_join.py`'s
  `join_events_to_gt` drops executions with `NaN` `start_ts`/`end_ts` before assignment (per the
  Phase 0 decision recorded in WORKLOG), so events inside those executions stay `unassigned` and
  never contribute a `true_boundary=1` label. This is consistent, not a new bug in 1F, but it does
  mean the reported GT boundary counts will always be a slight undercount relative to the full
  manifest.

### Whether it produced final segments / metrics

**No.** Zero output files exist. No segment count, no precision/recall/F1, no threshold value has
ever been materialized for Phase 1F. Nothing in the repo (committed or uncommitted) contradicts
the WORKLOG's own "pending final held-out results" note.

### Was it correct?

Based on static review only (not execution):
- The **design** matches the intended architecture (candidate generation and boundary decision as
  separate stages, sequence/context features, no GT-identity features, correct held-out protocol,
  chunk-crossing made explicit) and is consistent with everything learned in 1B/1B.1/1C/1D/1E.
- All dataframe columns it references (`active_app`, `window_title`, `browser_url`,
  `browser_tab_id`, `extracted_text`, `clipboard_text`, `chunk_id`, `execution_id`, etc.) do exist
  in the schema produced by Phase 0's normalizer/join (`src/normalizer.py`,
  `src/data_join.py`) — no obvious column-mismatch bug found by inspection.
- Two minor, non-disqualifying design questions: `event_index` as a feature, and `chunk_change` as
  a soft scoring signal.
- **But none of this has been confirmed to actually run.** I have not executed it in this session
  (the one attempt was declined), so I cannot confirm it produces a working result end-to-end,
  confirm the metrics are sane, or confirm there's no runtime error (e.g., an empty group,
  a dtype issue in the `context()` example-generation step, or a pipeline-indexing bug in
  `m[-1].coef_[0]`).

---

## Final status

**`PHASE 1F PARTIALLY COMPLETE`**

Reasoning: the code exists, is substantively written (not a stub), and — on static review — its
design is methodologically consistent with the intended architecture and shows no GT-identity
leakage and no train/held-out leakage. However, it has **never been executed**: there are no
output artifacts of any kind (no CSVs, no plots, no printed metrics) anywhere in the repository,
committed or uncommitted, and neither Phase 1E nor Phase 1F has ever been committed to git history
at all (history stops at Phase 1D, commit `c661371`). So while I found no evidence it is
*methodologically incorrect*, I also have no evidence it *works* — "partially complete" reflects
that the implementation is written but unverified and undelivered, not that it's known-broken.

**Phase 1E status: correctly implemented and complete as a diagnostic** (not a segmentation
method — it was never meant to be one). Its conclusion is well-supported by its own output data.

---

## Open questions for you before any further action

1. Do you want me to **execute** `src/phase1f_segmentation.py` now, purely to see whether it runs
   cleanly and what metrics it produces (read-only in the sense of not touching the pipeline code,
   though it will write its own output files into `phase1f_segmentation/`)? That's the fastest way
   to convert "partially complete" into either "correct and complete" or "implemented but broken."
2. If it turns out broken or the metrics are unacceptable, you already said: delete and reimplement
   rather than patch — confirming that's still the intent once we have an actual result to judge.
3. Neither Phase 1E nor Phase 1F is in git history yet. Do you want these committed as-is (to
   preserve the actual progression Codex made) before any reimplementation, so the history isn't
   lost?
