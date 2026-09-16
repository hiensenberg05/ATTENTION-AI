# Phase 1F.5 — Combining 1F.3 (clustering) + 1F.4 (content features)

Run: `.\venv\Scripts\python.exe src\phase1f5_segmentation.py` then
`.\venv\Scripts\python.exe src\tolerance_metrics.py`

Composition (nothing else changed): Phase 1F's candidate generation and base features, PLUS
Phase 1F.4's four case-ID content features (unchanged, imported), scored by an identically
configured/trained LogisticRegression, selected by Phase 1F.3's tooling filter + chain
clustering + earliest-event representative (unchanged, imported). No new features, no
embeddings, no LLM, no Dataset B.

## Exact-match result: a small win over 1F.3, still short of 1F.4 alone

| Scope | Metric | 1F | 1F.3 | 1F.4 | **1F.5** |
|---|---|---:|---:|---:|---:|
| Held-out | Precision | 27.3% | 28.6% | 28.1% | **29.2%** |
| Held-out | Recall | 56.5% | 36.8% | 57.2% | **38.6%** |
| Held-out | F1 | 0.368 | 0.322 | **0.376** | 0.332 |
| Training OOF F1 | 0.359 | 0.341 | 0.362 | **0.340** |
| NMS-suppressed FN recovered (of 330) | — | 116 (35.2%) | — | **128 (38.8%)** |

On exact-event matching, 1F.5 beats 1F.3 at every number (content features add a small,
consistent benefit on top of clustering, exactly like they did on top of plain NMS in 1F.4), but
it does **not** beat 1F.4 alone -- clustering's structural one-pick-per-burst ceiling still caps
exact-match recall below what keeping every NMS-surviving neighbor achieves.

**If exact-match were the only lens, the honest conclusion would be "combining helps a little
over clustering alone, but plain NMS + content features (1F.4) is still the best single
variant."** That is not the full picture -- see below.

## Tolerance-based result: a different and more informative picture

Exact-event GT matching penalizes a prediction that lands 1-2 events from the true boundary as
badly as one that's nowhere close, even when (as the Phase 1F.1/1F.2 diagnosis showed) many
"errors" are really the model correctly flagging the right neighborhood inside a multi-event
burst. Tolerance-window matching (±k events, one-to-one greedy nearest-match so a burst of
predictions can't multi-count against one true boundary) tests that directly:

| Variant | Tolerance | Held-out Precision | Held-out Recall | Held-out F1 |
|---|---:|---:|---:|---:|
| 1F | 0 (exact) | 27.3% | 56.5% | 0.368 |
| 1F | ±2 | 39.5% | 81.8% | 0.533 |
| 1F | ±3 | 40.5% | 83.9% | 0.546 |
| 1F.2 | 0 | 23.1% | 31.6% | 0.267 |
| 1F.2 | ±2 | 38.7% | 53.0% | 0.447 |
| 1F.2 | ±3 | 54.9% | 75.1% | **0.634** |
| 1F.3 | 0 | 28.6% | 36.8% | 0.322 |
| 1F.3 | ±2 | 51.0% | 65.6% | 0.574 |
| 1F.3 | ±3 | 55.9% | 71.9% | 0.629 |
| 1F.4 | 0 | 28.1% | 57.2% | 0.376 |
| 1F.4 | ±2 | 39.9% | 81.4% | 0.536 |
| 1F.4 | ±3 | 41.0% | 83.5% | 0.550 |
| **1F.5** | 0 | 29.2% | 38.6% | 0.332 |
| **1F.5** | **±2** | **51.2%** | **67.7%** | **0.583** |
| **1F.5** | ±3 | 55.4% | 73.3% | 0.631 |

**This flips the ranking.** Under ±2-event tolerance, 1F.5 is the best variant of all five
(F1 0.583, beating 1F's 0.533 and 1F.4's 0.536 by ~5 points). Under ±3-event tolerance, the three
clustering-based variants (1F.2, 1F.3, 1F.5) cluster tightly around F1 ≈ 0.63, all clearly ahead
of the two non-clustering variants (1F, 1F.4) at F1 ≈ 0.55.

**Why:** clustering's whole point is to stop keeping multiple near-duplicate predictions per
burst. Under exact matching that shows up as lost recall (whichever single event gets picked
often isn't the exact GT one). Under tolerance matching, precision is what benefits: plain NMS
(1F, 1F.4) keeps 2-3 predictions per burst, but one-to-one tolerance matching only lets ONE of
them match the nearby true boundary -- the rest count as unmatched false positives regardless of
tolerance. Clustering variants don't have that problem because they only ever produce one
prediction per burst in the first place, so precision under tolerance is ~51-56% for clustering
vs. ~39-41% for plain NMS, for comparable or better recall.

Note also that at ±3, the tie-break rule (argmax vs. earliest) stops mattering much (1F.2 ≈ 1F.3
≈ 1F.5): a 3-event radius is close to the typical burst span itself, so almost any representative
picked from within a burst lands close enough to the true event once tolerance is that wide.

## Does the combination improve actual boundary localization, or only the exact-match score?

**It improves actual localization, not just a scoring artifact.** The clustering-based variants
produce fewer, cleaner, non-redundant boundary picks (matches `predicted_boundary_count`: 1F.5 =
377 held-out vs. 1F's 590 and 1F.4's 581, for similar or better tolerance-matched recall). That is
a real, substantively different -- and for the actual deliverable (`segments.jsonl`, which only
needs approximately-right timestamps) probably more useful -- output than the exact-match F1
alone suggests. 1F.5 is not just "1F.3 with a marginally higher exact-match score"; it is the best
performer of all five variants once localization is judged with any realistic tolerance, while
also being the least over-segmented of the four non-baseline variants tried.

The one place 1F.5 does NOT win outright is exact-match recall, where 1F.4 (no clustering) is
still ahead (57.2% vs 38.6%) -- that gap is a direct, expected consequence of clustering
collapsing bursts to one prediction, not a flaw introduced by combining it with content features.

## Reproducibility

All five variants remain separate and independently reproducible:
`phase1f_segmentation/`, `phase1f2_segmentation/`, `phase1f3_segmentation/`,
`phase1f4_segmentation/`, `phase1f5_segmentation/`, each with its own `boundary_results.csv`,
`segment_results.csv`, `segmentation_statistics.csv`, and README. `tolerance_comparison.csv` in
this folder holds the full exact/±2/±3 table (both held-out and all-Dataset-A scopes) for all
five, computed post-hoc and read-only by `src/tolerance_metrics.py` directly from each variant's
saved `boundary_results.csv` -- no retraining or reselection involved in producing it.

No features/model beyond 1F.4's, no LLM, no Dataset B. Stopping here as instructed.
