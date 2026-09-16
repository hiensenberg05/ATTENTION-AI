# Phase 1F — Contextual boundary scoring and final Dataset A segmentation

Run: `.\venv\Scripts\python.exe src\phase1f_segmentation.py`

This final Dataset A evaluation uses candidates from every adjacent interaction-type change plus application/window/browser-context changes, gaps over one second, clipboard events, and browser navigation/form input. Chunk changes never force candidates or cuts.

Each candidate compares 20 events before and after: event-type composition; keyboard, mouse, browser, and clipboard mix; app/window/tab diversity and change rates; density/gaps; and availability (not content) of screen/clipboard text. Process identity, code/name, variant, execution ID, and all GT columns are excluded from scoring.

A class-balanced logistic model provides an interpretable scorer. Every fifth sorted session is a fixed held-out set. Its threshold is selected only from grouped five-fold out-of-fold predictions on training sessions, maximizing F1 after minimal three-event non-maximum suppression. The model then refits on all training sessions and is evaluated once on held-out sessions.

`boundary_results.csv` has all candidate scores and rare GT boundaries outside the pool. `segment_results.csv` is the chronological segmentation. Its `crosses_chunk` and `handling` fields make continuation across recording chunks explicit; chunks do not become process boundaries. Suspend/resume and split behavior gets no GT-derived rule: it is retained only when the contextual score clears the selected threshold.
