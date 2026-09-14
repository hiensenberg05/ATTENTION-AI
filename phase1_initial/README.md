# Initial Phase 1 — Boundary Signal Analysis

## Scope

Dataset A only. These results are diagnostic evidence, not a segmentation method.

## Findings

True boundaries are represented by adjacent timestamp-ordered events whose assigned GT execution changes. The analysis compares these pairs with all other adjacent event pairs. See `boundary_statistics.csv`, `signal_summary.csv`, and `boundary_examples.csv` for reproducible detail.

Temporal gaps are evaluated at 5, 10, 20, 30, and 60 seconds in `baseline_results.csv`. Gap-only results quantify why idle time cannot be treated as a conclusive business boundary. The gap-or-app-change baseline is included only as a diagnostic comparison: app switches and window changes also occur within GT executions.

Context and sequence evidence is retained as prior/current app, window, event type, gap, and change flags in `boundary_examples.csv`. This supports the next stage examining local context windows rather than assuming any single event is decisive.

## Special cases

GT contains continuation flags and split identifiers. These make one-to-one event-adjacent boundary labels incomplete: a process may suspend/resume, and a valid execution may lack `end_ts`. Chunk transitions are recording artifacts and are not promoted to boundaries here.

## Next stage recommendation

Investigate boundary candidates with short pre/post event windows, retain unassigned intervals, explicitly model GT continuation/split cases, and evaluate at execution level. Do not use Dataset B for tuning and do not equate app changes or chunks with process boundaries.
