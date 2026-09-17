# Phase 1F.3 — Cluster-and-pick with earliest-event representative

Run: `.\venv\Scripts\python.exe src\phase1f3_segmentation.py`

Same as Phase 1F.2 (chain clustering + tooling filter, scorer/features/candidate generation
unchanged from Phase 1F) except for one line: `cluster_boundaries` now picks the **earliest**
event in each cluster as the representative, instead of the highest-scoring one (1F.2's own
diagnosis showed argmax was right only 40% of the time because FP scores aren't reliably lower
than TP scores locally).

## Result: a real improvement over 1F.2, but still short of the Phase 1F baseline

| Scope | Metric | Phase 1F | Phase 1F.2 (argmax) | Phase 1F.3 (earliest) |
|---|---|---:|---:|---:|
| Held-out | Precision | 27.3% | 23.1% | **28.6%** |
| Held-out | Recall | 56.5% | 31.6% | **36.8%** |
| Held-out | F1 | 0.368 | 0.267 | **0.322** |
| NMS-suppressed FN (of 330) recovered as TP | | — | 1 (0.3%) | **116 (35.2%)** |
| Training OOF F1 | | 0.359 | 0.251 | 0.341 |

Picking "earliest in cluster" instead of "highest score in cluster" recovers most of what
argmax lost — the hypothesis from the 1F.2 diagnosis was directionally correct — but it still
doesn't beat plain greedy NMS on exact-event-match recall (36.8% vs 56.5%). The old NMS's
"bug" (accidentally keeping multiple candidates per burst when they happen to be pairwise
≥3 events apart) still nets more exact-match recall than a disciplined single-pick-per-cluster
design, under this exact-match evaluation.

This is worth flagging rather than glossing over: it suggests the *right* fix may not be a better
tie-break at all, but re-examining whether exact-event matching is the correct thing to be
optimizing against in the first place (see the tolerance-based-evaluation suggestion in
`WORKLOG.md`) — clustering produces structurally cleaner, non-redundant segment boundaries even
when it "loses" on an exact-match scoreboard.

Tooling filter effect is essentially unchanged from 1F.2 (1,431 flagged, 11 true boundaries
affected) — it is not the source of the difference between 1F.2 and 1F.3.
