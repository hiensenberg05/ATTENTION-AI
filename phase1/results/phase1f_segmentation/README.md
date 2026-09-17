# Phase 1F — Contextual boundary scoring and final Dataset A segmentation

Run: `.\venv\Scripts\python.exe src\phase1f_segmentation.py` (~1.5 minutes)

**Rewrite note (2026-09-16):** the original draft of this script was written but never
executed — no output files existed anywhere in the repo, and an audit (`PHASE_HANDOFF_AUDIT.md`)
found its non-maximum suppression compared candidate positions across *different* sessions
(session-local `event_index` values collide by coincidence between sessions), which could
suppress unrelated boundaries. The pipeline was rewritten: NMS is now grouped by `session_id`,
and the per-candidate context-window feature loop was switched from pandas `.iloc` slicing to
numpy array slicing, which is what actually makes the run finish in ~1.5 minutes instead of
never finishing. The methodology below is unchanged from the original design; the results are
from the first real, successful run.

This final Dataset A evaluation uses candidates from every adjacent interaction-type change plus application/window/browser-context changes, gaps over one second, clipboard events, and browser navigation/form input. Chunk changes never force candidates or cuts.

Each candidate compares 20 events before and after: event-type composition; keyboard, mouse, browser, and clipboard mix; app/window/tab diversity and change rates; density/gaps; and availability (not content) of screen/clipboard text. Process identity, code/name, variant, execution ID, and all GT columns are excluded from scoring.

A class-balanced logistic model provides an interpretable scorer. Every fifth sorted session is a fixed held-out set. Its threshold is selected only from grouped five-fold out-of-fold predictions on training sessions, maximizing F1 after minimal three-event non-maximum suppression. The model then refits on all training sessions and is evaluated once on held-out sessions.

`boundary_results.csv` has all candidate scores and rare GT boundaries outside the pool. `segment_results.csv` is the chronological segmentation. Its `crosses_chunk` and `handling` fields make continuation across recording chunks explicit; chunks do not become process boundaries. Suspend/resume and split behavior gets no GT-derived rule: it is retained only when the contextual score clears the selected threshold.

## Results (first real run)

Candidate pool: 108,913 candidates (67% of all 162,768 events), **100% boundary recall** at the
candidate stage — every GT boundary survives candidate generation, so all recall loss happens at
scoring/selection, as intended. Selected threshold: 0.83 (from training-only grouped 5-fold OOF
search, tie-broken toward the higher/more conservative threshold on ties). Training OOF F1 0.359,
close to the held-out F1 below — no sign of threshold-selection leakage.

| Metric | Held-out sessions | All Dataset A |
|---|---:|---:|
| Boundary precision | 27.3% | 26.5% |
| Boundary recall | 56.5% | 60.8% |
| Boundary F1 | 0.368 | 0.369 |
| Predicted / GT boundaries | 590 / 285 | 3,170 / 1,382 |
| Predicted segments | 603 | 3,233 |
| Median segment duration | 19.3s | 19.3s |
| Segments crossing a chunk | 11 | 45 |

This is a real improvement over the Phase 1B naive per-transition classifier (88.4% recall /
6.2% precision at threshold 0.5, F1 ≈ 0.12), but it still roughly doubles the number of segments
relative to ground truth (over-segmentation) and misses ~44% of true boundaries on held-out
sessions. Whether this is "good enough" for Dataset B analysis, or whether it needs another
scoring/threshold iteration first, is an open decision — not yet made.
