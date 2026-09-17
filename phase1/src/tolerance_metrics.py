"""Tolerance-window boundary matching, applied post-hoc to any Phase 1F-family
boundary_results.csv. Read-only evaluation utility -- does not retrain or reselect anything.

A predicted boundary counts as correct if it falls within `tolerance` events of a true boundary
in the SAME session, using one-to-one greedy nearest-distance matching: each predicted and each
true boundary can be consumed by at most one match. This matters -- a naive "is there a true
boundary within k events" count would let one cluster of 3 nearby predictions inflate recall by
matching the same true boundary three times, and would let one true boundary satisfied by 3
nearby predictions inflate precision the same way. One-to-one matching avoids both.

tolerance=0 reduces to exact-event matching and should reproduce each pipeline's own saved
segmentation_statistics.csv numbers exactly -- used as a self-check.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd


def tolerance_match_session(true_idx, pred_idx, tolerance):
    true_idx = np.asarray(sorted(true_idx))
    pred_idx = np.asarray(sorted(pred_idx))
    pairs = []
    for pi, p in enumerate(pred_idx):
        lo = np.searchsorted(true_idx, p - tolerance, side='left')
        hi = np.searchsorted(true_idx, p + tolerance, side='right')
        for ti in range(lo, hi):
            pairs.append((abs(int(true_idx[ti]) - int(p)), pi, ti))
    pairs.sort(key=lambda x: x[0])
    used_pred, used_true = set(), set()
    matched = 0
    for _, pi, ti in pairs:
        if pi in used_pred or ti in used_true:
            continue
        used_pred.add(pi)
        used_true.add(ti)
        matched += 1
    return matched, len(pred_idx), len(true_idx)


def evaluate(boundary_results, tolerance, scope=None):
    df = boundary_results
    if scope == 'heldout':
        df = df[df.split == 'heldout']
    total_matched = total_pred = total_true = 0
    for _, g in df.groupby('session_id', sort=False):
        true_idx = g.loc[g.true_boundary == 1, 'event_index'].to_numpy()
        pred_idx = g.loc[g.predicted_boundary == 1, 'event_index'].to_numpy()
        m, npred, ntrue = tolerance_match_session(true_idx, pred_idx, tolerance)
        total_matched += m
        total_pred += npred
        total_true += ntrue
    precision = total_matched / total_pred if total_pred else 0.0
    recall = total_matched / total_true if total_true else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        'tolerance': tolerance, 'scope': scope or 'all_dataset_a',
        'precision': precision, 'recall': recall, 'f1': f1,
        'matched': total_matched, 'predicted': total_pred, 'true': total_true,
    }


def evaluate_variant(name, boundary_results_path):
    df = pd.read_csv(boundary_results_path, usecols=['session_id', 'event_index', 'true_boundary', 'predicted_boundary', 'split'])
    rows = []
    for scope in ('heldout', 'all_dataset_a'):
        for tol in (0, 2, 3):
            r = evaluate(df, tol, scope=None if scope == 'all_dataset_a' else scope)
            r['variant'] = name
            rows.append(r)
    return rows


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2] / 'phase1' / 'results'
    variants = {
        '1F': root / 'phase1f_segmentation' / 'boundary_results.csv',
        '1F.2': root / 'phase1f2_segmentation' / 'boundary_results.csv',
        '1F.3': root / 'phase1f3_segmentation' / 'boundary_results.csv',
        '1F.4': root / 'phase1f4_segmentation' / 'boundary_results.csv',
        '1F.5': root / 'phase1f5_segmentation' / 'boundary_results.csv',
    }
    all_rows = []
    for name, path in variants.items():
        if not path.exists():
            print(f'skip {name}: {path} not found', file=sys.stderr)
            continue
        all_rows.extend(evaluate_variant(name, path))
    out = pd.DataFrame(all_rows)[['variant', 'scope', 'tolerance', 'precision', 'recall', 'f1', 'matched', 'predicted', 'true']]
    out.to_csv(root / 'phase1f5_segmentation' / 'tolerance_comparison.csv', index=False)
    pd.set_option('display.width', 140)
    print(out.to_string(index=False))
