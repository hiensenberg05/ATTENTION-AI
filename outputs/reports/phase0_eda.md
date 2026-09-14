# Phase 0 EDA Findings

Generated reproducibly by `python -m src.run_phase0`.

## Scope

This report documents data foundation and quality findings only. It does not segment Dataset B, rank automation candidates, or design an automation.

## Rules encoded in the pipeline

- Raw JSONL, manifests, GT, and screenshots are read-only inputs.
- JSONL parse failures are retained in `outputs/profiles/malformed_jsonl.csv`.
- Event rows retain source file and original line number.
- Events are assigned to GT only when their timestamp is in a valid half-open interval `[start_ts, end_ts)`.
- Events outside valid GT executions, including executions lacking `end_ts`, remain `unassigned`.
- Screenshots are not required for the normalization pipeline; their availability must be checked from event references versus files.

## Produced tables

- `dataset_a_events.parquet`
- `dataset_b_events.parquet`
- `dataset_a_gt_raw.parquet`
- `dataset_a_gt_executions.parquet`
- `dataset_a_events_with_gt.parquet`
- `dataset_a_process_features.parquet`

Profiles and validation findings are placed in `outputs/profiles/`.
