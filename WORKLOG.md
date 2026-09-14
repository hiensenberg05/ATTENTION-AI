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

