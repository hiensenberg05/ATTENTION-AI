# Phase 1A — Boundary Context Analysis

Dataset A only; no segmentation algorithm or clustering is implemented.

True-boundary windows are formed around adjacent GT-assigned events whose execution changes. Within-process windows are a deterministic random sample of adjacent events with unchanged execution. The 10, 20, and 50-event pre/post summaries are in `context_statistics.csv`; row-level evidence is in `boundary_context_examples.csv`.

Context differences should be interpreted as complementary evidence, not rules: temporal density, application/window diversity, browser/clipboard/keyboard/mouse composition, dominant event/app, and pre/post app-set similarity are compared together. The initial analysis already establishes that app changes must not be used alone.

Continuation and split cases remain structurally difficult because GT includes interrupted and missing-end executions; chunks are recording units, not positive labels. The next design stage should investigate calibrated local-window features, explicit abstention/unassigned treatment, and execution-level validation—not single-event triggers.
