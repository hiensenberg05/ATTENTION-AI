# Phase 1B — First Segmentation Baseline

Dataset A only. An interpretable logistic-regression transition model predicts whether the adjacent event transition is a GT execution boundary. Features are local temporal gap, app/window changes, and 10/20-event pre-transition interaction composition (browser, keyboard, clipboard, clicks). Process code, family, variant, and Dataset B are excluded from features.

Sessions are held out by session ID (every fifth sorted session). `model_results.csv` compares this model to gap-only diagnostics. The current output is transition predictions; the next approved stage should calibrate thresholds and construct/validate complete segments, including continuation and split cases. No Dataset B segmentation or clustering has occurred.
