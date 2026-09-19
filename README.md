# Attention AI

## Author Credentials

- Name: Uttkarsh Solanki
- Roll number: 23CH3EP19
- University: IIT Kharagpur
- Department: B.Tech. (Hons.) in Chemical Engineering and Master of Engineering Entrepreneurship
- EMAIL: uttkarsh2003.solanki@gmail.com
- PROTOTYPE LINK: https://attention-ai-1-tdm2.onrender.com/
- VIDEO LINK: https://drive.google.com/file/d/1sNCFkuxvyHBZfzR4JuNF2YwTh6xlnzu9/view
## Project Overview

Attention AI analyzes desktop operation logs to recover units of work and identify automation opportunities. It also includes a Step 3 prototype for bounded HR workflows. The backend combines deterministic policy checks, optional LLM decisions, Python state-machine orchestration, Playwright execution, and independent verification.

## Repository Structure

```text
DATA_SCHEMA.md          Input data specification
dataset_a/              Operation logs with ground truth
dataset_b/              Operation logs without ground truth
src/                    Shared Phase 0 loading, parsing, validation, and features
outputs/                Phase 0 generated tables and profiles
phase1/src/             Dataset A experiments and segmentation scripts
phase1/results/         Dataset A metrics and experiment outputs
phase2/src/             Dataset B segmentation and process-analysis scripts
phase2/results/         Dataset B segments, summaries, candidates, and plots
deliverables/           Final Step 1 output, final report, and work log
backend/                FastAPI service, workflows, mock HR app, and Python tests
frontend/               React + Vite operations console
Dockerfile              Multi-stage backend plus frontend production image
tests/                  Additional project tests
```

## Requirements

- Python 3.12 or newer
- Node.js 22 or newer and npm
- Git
- Docker Desktop, only when using the container workflow
- Chromium installed through Playwright for browser-backed tests and execution

## Initial Setup

Run these commands from the repository root.

### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
```

### macOS or Linux

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
```

The project uses one Python environment for Phase 0, Phase 1, Phase 2, the backend, and the tests. Optional LLM configuration is read from a root `.env` file. Set `GROQ_API_KEY` there to enable the Groq decision layer; without it, the deterministic policy fallback remains available.

## Run Phase 0: Load and Validate Data

Phase 0 parses both datasets, normalizes events, validates Dataset A ground truth, joins Dataset A events to executions, and writes reproducible tables and profiles.

```powershell
python src\run_phase0.py
```

Outputs are written to `outputs/tables/` and `outputs/profiles/`.

## Run Phase 1: Dataset A Segmentation

Dataset A has ground truth and is used to develop and measure boundary detection. The scripts are progressive experiments; each writes results under `phase1/results/`.

```powershell
# Initial exploration and signal studies
python phase1\src\phase1_initial.py
python phase1\src\phase1a_boundary_context.py
python phase1\src\phase1b1_diagnosis.py
python phase1\src\phase1b_segmentation.py
python phase1\src\phase1c_candidate_generation.py
python phase1\src\phase1d_signal_coverage.py
python phase1\src\phase1e_interaction_sequences.py

# Segmentation experiments
python phase1\src\phase1f_segmentation.py
python phase1\src\phase1f2_segmentation.py
python phase1\src\phase1f3_segmentation.py
python phase1\src\phase1f4_segmentation.py
python phase1\src\phase1f5_segmentation.py
```

Phase 1F.5 is the frozen pipeline used by Phase 2. Its outputs include boundary metrics, segment results, calibration, feature weights, and plots in `phase1/results/phase1f5_segmentation/`.

To calculate tolerance-window metrics for a generated boundary result:

```powershell
python phase1\src\tolerance_metrics.py
```

## Run Phase 2: Dataset B Analysis

Phase 2 reproduces and verifies the frozen Phase 1F.5 fit using Dataset A, applies it to Dataset B, groups recovered segments into process families, and creates the automation-candidate analysis.

Run the scripts in this order:

```powershell
python phase2\src\phase2_dataset_b_segmentation.py
python phase2\src\phase2_process_analysis.py
python phase2\src\phase2_process_summary.py
```

All Phase 2 outputs are written to `phase2/results/`. The main files are:

- `segments.jsonl`: required Step 1 output format
- `segment_features.csv`: per-segment audit table
- `process_summary.csv`: process-family aggregate statistics
- `variant_analysis.csv`: within-process variants
- `automation_candidates.csv`: candidate impact, feasibility, evidence, and risk
- `representative_segments.csv`: examples for manual verification
- `phase2_summary.md`: full analysis and uncertainty discussion

The committed deliverable is also available at `deliverables/segments.jsonl`.

## Deliverables and Results

The `deliverables/` folder contains the submission-facing files:

```text
deliverables/
├── segments.jsonl                 Step 1 Dataset B segmentation output
├── Attention AI - Final Report.pdf Final report
└── WORKLOG.md                     Development work log
```

The complete analysis results remain organized by phase:

```text
phase1/results/                    Dataset A experiments and validation metrics
phase2/results/
├── phase2_summary.md              Analysis summary and limitations
├── segments.jsonl                 Dataset B segmentation result
├── segment_features.csv           Per-segment features and audit data
├── process_summary.csv            Process frequency and time summary
├── variant_analysis.csv           Process-variant analysis
├── automation_candidates.csv      Prioritized automation candidates
├── representative_segments.csv   Representative examples for review
├── dashboard_data.json            Dashboard-ready metrics
└── plots/                         Generated charts and visual evidence
```

To regenerate these results, run the Phase 0, Phase 1, and Phase 2 commands above in
order. The Phase 2 result files are written to `phase2/results/`, while the required
submission segmentation file is available at `deliverables/segments.jsonl`.

## Run the Backend Prototype

Start from the repository root. Activate the virtual environment, then change into
the backend directory and start the API:

```powershell
\.\venv\Scripts\Activate.ps1
cd backend
uvicorn main:app --reload
```

On macOS or Linux:

```bash
source ./venv/bin/activate
cd backend
uvicorn main:app --reload
```

Useful URLs:

- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health
- Mock leave application: http://127.0.0.1:8000/mock-hr/leave-applications
- Mock payroll queue: http://127.0.0.1:8000/mock-hr/payroll-items

The backend supports Leave Approval and Payroll Confirmation. Set `PLAYWRIGHT_HEADLESS=false` in `.env` to watch browser execution. The backend uses a deterministic policy engine when `GROQ_API_KEY` is not configured.

## Run the Frontend Console

Keep the backend terminal running. Open a second terminal, activate the same virtual
environment if needed, then start the frontend from its directory:

```powershell
\.\venv\Scripts\Activate.ps1
cd frontend
npm install
npm run dev
```

On macOS or Linux, use a second terminal:

```bash
source ./venv/bin/activate
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite development server proxies `/api` requests to the backend. Available screens include the overview, workflow queue, agent decisions, execution trace, human review queue, and audit history.

## Run Tests and Checks

```powershell
# From the repository root, with the Python environment active
python -m pytest

# Frontend checks
cd frontend
npm run test
npm run typecheck
npm run lint
npm run build
```

Backend tests should be run with the root environment active. Browser-backed tests require the Playwright Chromium installation from the setup step.

## Run with Docker

The multi-stage image builds the React frontend and serves it through FastAPI.

```powershell
docker build -t attention-ai .
docker run --rm -p 8000:8000 attention-ai
```

Open http://127.0.0.1:8000. Docker is not required for the local development workflow. The image requires Docker Desktop with enough memory for Python packages and the Chromium browser.

## Important Notes

- Dataset B has no ground truth; its counts and process boundaries are analytical estimates and should be reviewed with the evidence tables and screenshots.
- The mock HR application and demo records are not production systems or production approval policies.
- Never commit `.env`, API keys, or other secrets.
DELEVIRABLES FOLDER CONTAINS RESULT
