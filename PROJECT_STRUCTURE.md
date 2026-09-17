# Project structure

`README.md` at the root is the assignment brief, unmodified. This file is the map
of what was built against it.

```
AI Engineer/
├── README.md                 the assignment brief (not mine — left untouched)
├── PROJECT_STRUCTURE.md      this file
├── DATA_SCHEMA.md            the raw log schema, as observed
├── PHASE_HANDOFF_AUDIT.md    the audit that ended the first attempt at Phase 1
│
├── deliverables/             ← what gets submitted, in one place
│   ├── README.md             the four deliverables and their status
│   ├── segments.jsonl        deliverable 1 — written here by the Phase 2 pipeline
│   ├── FINAL_REPORT.md       deliverable 3 — NOT WRITTEN YET (scaffold only)
│   └── WORKLOG.md            deliverable 4 — dated log, incl. how AI was used
│
├── requirements.txt          ← the ONLY dependency file
├── venv/                     ← the ONLY virtual environment
├── .env.example              template; the real .env is never committed
│
├── dataset_a/                63 sessions, with ground truth
├── dataset_b/                15 sessions, no ground truth
│
├── src/                      Phase 0: loading, parsing, normalising, joining
├── outputs/                  Phase 0 output: the parquet event tables
│   ├── tables/               dataset_a_events_with_gt.parquet, dataset_b_events.parquet, …
│   ├── profiles/             data-quality profiles
│   └── reports/phase0_eda.md
│
├── phase1/                   Step 1 — recover units of work (Dataset A, measured)
│   ├── README.md             what each script answered, and in what order
│   ├── src/                  13 scripts
│   └── results/              one directory per script: README.md + CSVs + plots
│
├── phase2/                   Step 2 — discover processes, find automation candidates
│   ├── README.md
│   ├── src/                  3 scripts
│   └── results/              summary, CSVs, plots, + its own segments.jsonl
│
├── backend/                  Step 3 — the prototype: agent, policy, executor, mock HR
└── frontend/                 Step 3 — the operator console
```

## One environment, one requirements file

There used to be two of each (a root venv for the analysis, a `backend/.venv` for
the prototype). There is now one of each, at the root.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium     # one-time, for the Step 3 executor
```

```bash
# macOS / Linux
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && python -m playwright install chromium
```

Versions are pinned rather than ranged. Phase 1's scorer and Phase 2's
`segments.jsonl` are reproducible outputs, and a silent minor-version bump in
numpy or scikit-learn is exactly what would break that quietly.

## Running each phase

Every script resolves the repo root from its own file location, so the working
directory does not matter. With the venv active:

```powershell
# Phase 0 — build the event tables the rest of the project reads (run once)
python src\run_phase0.py
python src\build_stage2.py

# Phase 1 — segmentation on Dataset A
python phase1\src\phase1f_segmentation.py     # baseline
python phase1\src\phase1f5_segmentation.py    # the selected variant
python phase1\src\tolerance_metrics.py        # compare all five 1F variants

# Phase 2 — apply the frozen scorer to Dataset B
python phase2\src\phase2_dataset_b_segmentation.py
python phase2\src\phase2_process_analysis.py
python phase2\src\phase2_process_summary.py   # writes segments.jsonl (both copies)

# Phase 3 — the prototype
cd backend
python -m uvicorn main:app --reload --port 8000
python -m pytest                              # 76 tests, incl. real browser runs

cd ..\frontend
npm install && npm run dev
```

Phase 2 depends on Phase 1: `phase2/src/` imports the Phase 1F modules directly
and puts `phase1/src/` on the path itself.

## The two copies of `segments.jsonl`

`deliverables/segments.jsonl` is the submitted file; `phase2/results/segments.jsonl`
is the phase output. They are not a file and a copy of it —
`phase2/src/phase2_process_summary.py::write_segments_jsonl` writes both paths from
the same string in the same function, so the submitted file cannot silently fall
behind a rerun. Do not replace this with a copy step.

## What is committed, and what is not

The Phase 1 and Phase 2 **result tables are committed** — they back every number
in the report, so they should be checkable without a rerun.

Two deliberate exceptions:

| Not committed | Why | How to rebuild |
|---|---|---|
| `phase1/results/**/boundary_results.csv` | ~66 MB per variant, ~330 MB total | rerun the matching `phase1f*_segmentation.py` |
| `outputs/tables/*.parquet` | regenerable in one step | `python src\run_phase0.py` |

Never committed: `.env`, `venv/`, `node_modules/`, browser binaries, caches.

## Reproducibility

Nothing in Phase 1 or Phase 2 is random. The scorer is a logistic regression with
a fixed `random_state` and fixed `GroupKFold` splits; Phase 2's grouping is
rule-based single-linkage at a fixed threshold. After the reorganisation both were
rerun and checksummed against the committed results:

| Output | Checksum after rerun |
|---|---|
| `phase1/results/phase1f_segmentation/segment_results.csv` | `26d3686f…` — unchanged |
| `phase2/results/segments.jsonl` | `54efb1b5…` — unchanged, 226 segments |

`phase2/src/phase2_dataset_b_segmentation.py` goes further: it re-fits Phase 1F.5
from scratch and **refuses to run** unless it reproduces 1F.5's recorded threshold
(0.88) and OOF F1 (0.3404874499818116) exactly.
