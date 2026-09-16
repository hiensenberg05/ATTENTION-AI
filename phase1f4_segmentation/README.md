# Phase 1F.4 — Case-ID content features (original NMS post-processing, unchanged)

Run: `.\venv\Scripts\python.exe src\phase1f4_segmentation.py`

Isolates the effect of adding content-derived features to the scorer, holding post-processing
at Phase 1F's original greedy NMS (not 1F.2/1F.3's clustering) so this result is directly
comparable to the Phase 1F baseline without confounding it with the post-processing experiments.

Four new candidate-level features, computed from `extracted_text`/`clipboard_text` in the same
±20-event windows every other feature already uses, via a simple regex
(`[A-Z]{2,5}-\d{4,10}(-\d{2,4})?`) that reliably extracts case IDs like `INV-071644-001`,
`EXP-132513-02`, `SHIP-2026-3084`:

- `pre_has_case_id` / `post_has_case_id` — any case-ID-shaped token found in that side's window
- `case_id_changed` — a case ID is found on both sides and the sets are disjoint (new case)
- `case_id_persists` — a case ID is found on both sides and they overlap (same case, different step)

No GT identity involved — this is OCR'd/captured screen text, a legitimately observable signal.

## Result: a small, real, consistent improvement

| Scope | Metric | Phase 1F (no content features) | Phase 1F.4 (with content features) |
|---|---|---:|---:|
| Held-out | Precision | 27.3% | **28.1%** |
| Held-out | Recall | 56.5% | **57.2%** |
| Held-out | F1 | 0.368 | **0.376** |
| All Dataset A | F1 | 0.369 | **0.372** |
| Training OOF F1 | 0.359 | **0.362** |

Small in absolute terms, but the direction is consistent across training OOF *and* held-out
(not just held-out noise), and both precision and recall move the same way — a genuine, if
modest, improvement.

## Why the effect is modest, not transformative — exactly as predicted before running it

Feature prevalence across all 108,913 candidates: `pre_has_case_id` fires on 56.3% of them,
`post_has_case_id` on 61.2%. That's much higher than the flat 4.48% per-event extracted_text
coverage would suggest, because a 20-event window has a high chance of containing *at least one*
event with text somewhere in it (≈1-(1-0.045)^20 ≈ 61%, matching what's observed) — but that
means "has a case ID somewhere in this ±20-event span" is a broad, low-precision signal, not "the
exact screen at this transition shows a case ID." The tighter, more informative features are the
relational ones:

- `case_id_changed` fires on only 9.3% of all candidates but 2.7% of true boundaries — informative
  but rare.
- `case_id_persists` fires on 22.0% of all candidates and 20.9% of true boundaries.

Learned coefficients (class-balanced logistic regression, same as Phase 1F): `case_id_changed`
+0.228, `case_id_persists` +0.209, `post_has_case_id` -0.132, `pre_has_case_id` -0.011 — sensible
signs (a changed or persisting case ID nudges the score up), but small relative to the dominant
sparse event-type features (which run into the ±3-4 range). This matches the earlier finding from
the manual case-ID diff test: only 101/1382 boundaries (7.3%) have a clean case-ID-changed signal
available, and 69% of boundaries with an extractable ID show the *same* ID before and after
(a process-type switch on the same case, not a new case) — so this feature can only ever directly
resolve a minority of the remaining error, which is exactly what the result shows.

## Bottom line across all four Phase 1F variants tried

| Variant | Held-out F1 | Notes |
|---|---:|---|
| Phase 1F (baseline) | 0.368 | greedy NMS, no content features |
| Phase 1F.2 | 0.267 | clustering + argmax representative — regression |
| Phase 1F.3 | 0.322 | clustering + earliest representative — better than 1F.2, still below baseline |
| **Phase 1F.4** | **0.376** | **baseline NMS + case-ID content features — best so far** |

The content-feature addition (1F.4) is the only one of the three experiments that beat the
original Phase 1F baseline, though only marginally. It was not combined with the clustering
experiments (1F.2/1F.3) in this round — that combination (earliest-in-cluster + content features
together) is a natural next experiment but wasn't run here.
