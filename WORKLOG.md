# Phase 0 Work Log

## 2026-09-14

- Investigated: README, DATA_SCHEMA, raw events/manifests from both datasets, and Dataset A GT streams/manifests.
- Findings: session/chunk boundaries differ from process boundaries; line order is not always timestamp order; extracted text is sparse; screenshot manifests substantially overstate present files.
- Implemented: reusable discovery, streaming parser, flat normalizer, GT parser/validator, half-open event-to-GT join, process features, and reproducible output runner.
- Decision: preserve raw sources untouched; retain malformed-record reports and source line traceability; do not use missing-end GT executions for temporal assignment.
- AI assistance used: assisted schema inspection, EDA design, and implementation.
- Next step: run the pipeline, inspect outputs/tests, document Phase 0 results. No segmentation work has been started.

## 2026-09-14 — Initial Phase 1

- Investigated: Dataset A GT-aligned adjacent events, gaps, application/window changes, event taxonomy, continuations and splits.
- Implemented: diagnostic gap and gap-or-app-change baselines only; no segmentation, clustering, classifier, or Dataset B labeling.
- Next step: await approval before a segmentation-design stage.


## 2026-09-14 — Phase 1A
- Investigated: 10/20/50-event pre/post behavioral windows at GT execution changes against sampled within-execution transitions.
- Implemented: context statistics and diagnostic comparisons only; no segmentation or Dataset B tuning.
- Next step: await approval for segmentation design.


## 2026-09-15 — Phase 1B.1
- Diagnosed existing held-out model only: imbalance, probability overlap, threshold sweep, coefficients, and error examples.
- No retraining, Dataset B use, clustering, or pipeline redesign performed.


## 2026-09-15 — Phase 1C
- Built Dataset A-only weak-signal candidate generation and compact contextual representation.
- No final segmentation or Dataset B work.


## 2026-09-15 — Phase 1D
- Diagnosed all Dataset A GT boundary signal coverage; no candidate-generator change or ranking implemented.


## 2026-09-15 — Phase 1F
- Built the final Dataset A-only high-recall candidate plus contextual scorer segmentation pipeline.
- Used no Dataset B, process clustering, LLM, or Step 3 work; model features exclude process identity/code/variant and GT columns.
- Threshold is chosen with grouped training-only out-of-fold calibration; pending final held-out results.
