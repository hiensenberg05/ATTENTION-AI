# Phase 1B.1 — Boundary Model Diagnosis

Dataset A held-out sessions only. The existing logistic model is not retrained or tuned here.

## Class imbalance

The held-out transitions contain 285 positives and 26,717 negatives (1.06% positive). Even a modest false-positive rate therefore creates many incorrect cuts. The `class_weight=balanced` training choice increases sensitivity but plausibly contributes to the large predicted-boundary count at 0.5.

## Probability overlap

The true-boundary median score is 0.781 and non-boundary median is 0.167, showing useful ranking signal but substantial overlap, as shown in `plots/probability_overlap.png`. A score is not calibrated evidence of a usable cut.

## Features and errors

Feature coefficients are preserved in `feature_analysis.csv`. Error files retain high-score false positives and low-score false negatives for inspection. Gap, application/window change, and short context proportions cannot independently represent interruption, continuation, unassigned work, or execution semantics.

## What is actually limiting the current model?

Extreme transition-level imbalance, probability overlap, and feature granularity. The model evaluates each transition independently and has no candidate-generation or sequential consistency constraint; balanced training then turns weak local changes into excessive cuts.

## Recommendation for the next segmentation iteration

Before retraining, investigate a two-stage formulation: high-recall candidate generation followed by calibrated ranking using richer pre/post sequence features and session-level temporal constraints. Evaluate tolerance-based boundary matching and explicit continuation/split handling. Do not use Dataset B for tuning.
