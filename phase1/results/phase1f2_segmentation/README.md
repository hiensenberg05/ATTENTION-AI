# Phase 1F.2 — Cluster-and-pick post-processing + tooling filter (result: regression, not an improvement)

Run: `.\venv\Scripts\python.exe src\phase1f2_segmentation.py` (~1.5 minutes)

Reuses Phase 1F's feature engineering, candidate generation, and model training **unchanged**
(imported from `src/phase1f_segmentation.py`, not reimplemented — verified bit-for-bit identical
scores, see §4). Only the post-processing changed: greedy 3-event NMS was replaced with
transitive chain clustering + highest-score-per-cluster selection, and a conservative, GT-free
tooling/background filter was added ahead of selection. No feature, no model, no LLM, no
Dataset B.

## Headline result: this made things worse, not better

| Scope | Metric | Phase 1F (before) | Phase 1F.2 (after) |
|---|---|---:|---:|
| Held-out | Precision | 27.3% | **23.1%** (↓) |
| Held-out | Recall | 56.5% | **31.6%** (↓↓) |
| Held-out | F1 | 0.368 | **0.267** (↓) |
| Held-out | Predicted / GT boundaries | 590 / 285 | 390 / 285 |
| Held-out | Predicted segments | 603 | 403 |
| All Dataset A | Precision | 26.5% | **20.9%** (↓) |
| All Dataset A | Recall | 60.8% | **31.1%** (↓↓) |
| All Dataset A | F1 | 0.369 | **0.250** (↓) |
| All Dataset A | Predicted / GT boundaries | 3,170 / 1,382 | 2,057 / 1,382 |
| Training OOF F1 (calibration objective) | | 0.359 | **0.251** (↓) — worse even in-sample, not just held-out noise |

Segment counts dropped a lot (603→403 held-out), which looks like "less over-segmentation," but
it is **not a real improvement** — it happened because both true and false positives collapsed
together, and precision got *worse*, not better. This is a genuine regression versus Phase 1F, not
a trade-off with an upside.

## 1. Isolating the cause: it's the clustering algorithm itself, not the threshold or the filter

Recalibrating the threshold *and* changing the selection algorithm at the same time would
confound which change caused the regression, so this was isolated by re-running both post-
processing methods at the identical fixed threshold (0.83, Phase 1F's own value), on identical
(bit-for-bit verified, see §4) scores, held-out sessions only:

| Method | Threshold | Precision | Recall | F1 | Predicted |
|---|---:|---:|---:|---:|---:|
| Old greedy NMS (Phase 1F) | 0.83 | 0.273 | 0.565 | 0.368 | 590 |
| Cluster + argmax, no tooling filter | 0.83 | 0.224 | 0.319 | 0.263 | 407 |
| Cluster + argmax, with tooling filter | 0.83 | 0.223 | 0.316 | 0.262 | 403 |
| Old greedy NMS (counterfactual) | 0.87 | 0.281 | 0.540 | 0.370 | 548 |
| Cluster + argmax, with filter (actual 1F.2 config) | 0.87 | 0.231 | 0.316 | 0.267 | 390 |

The tooling filter moves the numbers by less than a point either way. The threshold recalibration
(0.83→0.87) barely moves old NMS either (F1 0.368→0.370). **The clustering algorithm alone
accounts for essentially the entire regression** (F1 0.368→0.263 at the same threshold, same
filter status).

## 2. Root cause: "highest score in the cluster" is not a reliable way to find the true boundary

Among the 227 held-out clusters (threshold 0.83, no filter) that actually contain a true
boundary, the highest-scoring member **was** the true boundary in only 91 of them (40.1%). In the
other 136 (59.9%), a neighboring non-boundary candidate scored higher and got picked instead.
Examples (event_index / score / true_boundary per cluster member):

```
[160, 163]                          scores [0.918, 0.946]                    true=[1, 0]   -> picked 163 (wrong)
[608, 610, 611]                     scores [0.877, 0.859, 0.951]             true=[1, 0, 0] -> picked 611 (wrong)
[672, 673, 674, 675, 677, 678]      scores [.842,.902,.872,.960,.964,.983]   true=[0,0,0,1,0,0] -> picked 678 (wrong)
```

This lines up exactly with the Phase 1F.1 diagnosis finding that **FP scores are not lower than
TP scores on average (FP median 0.964 vs TP median 0.936, dataset-wide)**. Clustering correctly
solves the *structural* problem (a burst around one real switch no longer produces multiple
independent NMS picks) but the *representative-selection rule* — pick the single highest score —
is actively miscalibrated for this scorer, because within a local burst the false neighbors are, if
anything, slightly more likely to out-score the real boundary than to score lower than it. The old
NMS's accidental tendency to keep *multiple* candidates per burst (whenever they happened to be
individually ≥3 events apart from whichever was accepted first) meant it more often included the
true boundary among its extra picks, even though that came at the cost of extra FPs too.

This directly explains the weak NMS-suppressed-FN recovery rate: of the 330 boundaries that scored
≥0.83 in Phase 1F but were NMS-suppressed, only **1** became a correctly-selected TP under
clustering. (The specific burst inspected in the Phase 1F.1 report — session `JAYESH`, events
751/753/754 — is that one success case: the tooling filter happened to remove the two neighboring
candidates at 748-752 as SYSTEM-adjacent, leaving 753 as the sole eligible member of its cluster.
That's a filter effect, not a clustering-selection effect, and it doesn't generalize to bursts the
filter doesn't touch.)

## 3. Tooling filter: safe, but a minor effect on its own

- 1,431 / 108,913 candidates (1.3%) flagged as tooling/background context.
- Only **11 of 1,382** GT true boundaries (0.8%) fall inside flagged candidates — the filter is
  conservative, as intended; it is not costing meaningful recall by itself.
- Only 61 flagged candidates would have cleared the 0.87 threshold anyway — so even without the
  regression from clustering, the filter's own ceiling for removing false positives in this run
  was small relative to the ~2,300 FPs Phase 1F actually produced. It is a real, safe, generic
  fix for the specific background-activity failure mode identified in Phase 1F.1, just not a
  large lever on the aggregate numbers by itself.

## 4. What stayed genuinely unchanged (verified, not assumed)

Compared candidate scores between `phase1f_segmentation/boundary_results.csv` and
`phase1f2_segmentation/boundary_results.csv` for all 108,913 shared `row_id`s: **max absolute
difference = 0.0**. The scorer, its features, and its training procedure are bit-for-bit
identical between the two runs, as required — every difference above comes only from
post-processing.

## Conclusion

As specified and implemented, Phase 1F.2's post-processing change is a regression, not an
improvement, and the cause is fully diagnosed and evidenced rather than left as a mystery: chain
clustering correctly fixes the burst-fragmentation *structure* the Phase 1F.1 audit found, but
"highest score wins" is the wrong tie-break given this scorer's actual calibration (FPs score at
least as high as TPs within local neighborhoods). The tooling filter itself is safe and correctly
targeted at the background-activity failure mode, but is a small effect next to the clustering
regression. Per instructions, no further implementation changes were made after this diagnosis —
reported and stopped.
