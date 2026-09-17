# Phase 1 — Recovering units of work from Dataset A

**Step 1 of the assignment.** Dataset A has ground truth (63 sessions, ~162,000
events), so this phase is where segmentation is *measured*. Nothing here reads
Dataset B, and nothing here is used to label Dataset B directly — Phase 2 reuses
the frozen scorer, not the ground truth.

```
phase1/
├── src/        the scripts, in the order they were written
└── results/    one directory per script: README.md, CSVs, plots
```

## Running it

From the repo root, with the single project venv active (see
[PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md)):

```powershell
python src\run_phase0.py                       # once: builds outputs/tables/*.parquet
python phase1\src\phase1f_segmentation.py      # the baseline scorer
python phase1\src\phase1f5_segmentation.py     # the selected variant
```

Every script resolves the repo root from its own location, so they can be run
from anywhere. Each writes only into its own `results/<name>/` directory.

## The scripts, and what each one answered

| Script | Result directory | Question it answered |
|---|---|---|
| `phase1_initial.py` | `phase1_initial/` | What does a naive gap-threshold segmenter score? (the baseline to beat) |
| `phase1a_boundary_context.py` | `phase1a_boundary_context/` | What does the event context around a true boundary actually look like? |
| `phase1b_segmentation.py` | `phase1b_segmentation/` | Can a supervised transition classifier beat the gap heuristic? |
| `phase1b1_diagnosis.py` | `phase1b1_diagnosis/` | Where is that classifier wrong, and is the threshold or the features to blame? |
| `phase1c_candidate_generation.py` | `phase1c_candidate_generation/` | How few candidate positions can we score without losing recall? |
| `phase1d_signal_coverage.py` | `phase1d_signal_coverage/` | Which boundary signals fire, and which boundaries emit no signal at all? |
| `phase1e_interaction_sequences.py` | `phase1e_interaction_sequences/` | Do interaction *sequences* catch the boundaries single signals miss? |
| `phase1f_segmentation.py` | `phase1f_segmentation/` | **The baseline pipeline**: candidates → features → logistic scorer → NMS |
| `phase1f2_segmentation.py` | `phase1f2_segmentation/` | Does relaxing non-maximum suppression recover the burst-fragmented boundaries? |
| `phase1f3_segmentation.py` | `phase1f3_segmentation/` | Does chain clustering with an earliest-event representative do it better? |
| `phase1f4_segmentation.py` | `phase1f4_segmentation/` | Do case-ID content features help where context switches are invisible? |
| `phase1f5_segmentation.py` | `phase1f5_segmentation/` | **The selected variant**: 1F.3 + 1F.4 composed. Do the two wins stack? |
| `tolerance_metrics.py` | prints a comparison | How do all five 1F variants compare across match tolerances? |

`phase1f1_error_diagnosis/` holds the manual error triage (`near_fp`, `far_fp`,
`low_fn`, `nms_fn`) that motivated 1F.2–1F.5. It has no script: it is the
reading of 1F's `boundary_results.csv` that decided what to try next.

## Dependencies between scripts

Most are independent. Three are not:

- `phase1b1_diagnosis.py` reads `phase1b_segmentation/`'s predictions.
- `phase1f2/1f3/1f5` read `phase1f_segmentation/boundary_results.csv` to compare
  against the baseline's suppressed false negatives.
- `phase1f5` imports 1F, 1F.2, 1F.3 and 1F.4 directly, as modules.

`boundary_results.csv` is the only result file not committed — it is ~66 MB per
variant. Rerun the matching script to rebuild it.

## Reproducibility

The scorer is a logistic regression with fixed `GroupKFold` splits and no random
initialisation, so reruns are bit-identical. `phase1f_segmentation/segment_results.csv`
was regenerated after the repo reorganisation and matched its previous checksum
exactly (`26d3686f…`), which is what makes the numbers in the report re-checkable
rather than merely reported.
