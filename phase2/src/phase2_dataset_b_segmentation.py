"""Phase 2A: apply the FROZEN Phase 1F.5 pipeline to Dataset B.

Phase 1F.5 (`phase1f5_segmentation.py`) never persisted its fitted model/threshold to disk --
they only existed inside that script's `main()` call. To "use Phase 1F.5 exactly as it currently
exists" against a different dataset, this script reproduces the identical, deterministic fit
procedure on Dataset A ONLY (same candidate generation, same feature engineering incl. Phase
1F.3's tooling filter and Phase 1F.4's case-ID features, same held-out split, same GroupKFold OOF
threshold search, same LogisticRegression hyperparameters/random_state), then applies that frozen
model + frozen threshold + frozen clustering (Phase 1F.3's earliest-event chain clustering) to
Dataset B. Every function used is imported unchanged from the existing Phase 1F modules -- nothing
about segmentation is retrained, re-tuned, or reselected using Dataset B.

`verify_frozen_reproduction()` checks the reproduced fit against Phase 1F.5's own saved
`experiment` numbers (threshold 0.88, training OOF F1 0.3405) as a correctness gate -- if this
does not match, the "frozen" claim would be false and the script refuses to proceed.

Dataset B has no ground truth, so `load_events_b` mirrors `p1f.load_events` exactly except it
never computes (and Dataset B's table never has) a `true_boundary`/`execution_id` column -- no
Dataset A GT is read for or applied to Dataset B at any point.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# Phase 2 builds directly on the frozen Phase 1F scorer, so Phase 1's modules
# must be importable. They live in a sibling folder, not on the default path.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'phase1' / 'src'))

import phase1f_segmentation as p1f
import phase1f3_segmentation as p1f3
import phase1f4_segmentation as p1f4

ROOT = p1f.ROOT
OUT = ROOT / 'phase2' / 'results'
OUT.mkdir(exist_ok=True)

EXPECTED_THRESHOLD = 0.88
EXPECTED_OOF_F1 = 0.3404874499818116


def fit_frozen_pipeline_on_dataset_a():
    """Reproduce Phase 1F.5's fit exactly. Deterministic: fixed random_state, fixed data, fixed
    feature code -- rerunning this always yields the same model/threshold, it is not a new fit."""
    e = p1f.load_events()
    e['candidate'] = p1f.candidate_mask(e)
    e['tooling_context'] = p1f3.compute_tooling_context(e)
    vocab = e.event_type.value_counts().head(p1f.VOCAB_SIZE).index.tolist()

    base = pd.concat([p1f.session_features(g, vocab) for _, g in e.groupby('session_id', sort=False)], ignore_index=True)
    content = pd.concat([p1f4.session_content_features(g) for _, g in e.groupby('session_id', sort=False)], ignore_index=True)
    candidates = base.merge(content, on='row_id', how='left')
    candidates['true_boundary'] = e.loc[candidates.row_id, 'true_boundary'].to_numpy()
    candidates['tooling_context'] = e.loc[candidates.row_id, 'tooling_context'].to_numpy()

    session_ids = sorted(e.session_id.unique())
    heldout_sessions = set(session_ids[::p1f.HOLDOUT_STRIDE])
    train = candidates[~candidates.session_id.isin(heldout_sessions)].copy()

    exclude = p1f.NON_FEATURE_COLUMNS | {'tooling_context'}
    feature_columns = [c for c in candidates.columns if c not in exclude and candidates[c].dtype != object]

    oof_rows = []
    for train_idx, val_idx in GroupKFold(n_splits=5).split(train, train.true_boundary, groups=train.session_id):
        fold_model = make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=1000, random_state=p1f.RANDOM_STATE))
        fold_model.fit(train.iloc[train_idx][feature_columns], train.iloc[train_idx].true_boundary)
        fold_val = train.iloc[val_idx].copy()
        fold_val['score'] = fold_model.predict_proba(fold_val[feature_columns])[:, 1]
        oof_rows.append(fold_val)
    oof = pd.concat(oof_rows, ignore_index=True)

    sweep = []
    for t in np.round(np.arange(0.05, 0.951, 0.01), 2):
        pred = oof.row_id.isin(p1f3.cluster_boundaries(oof, float(t))).astype(int)
        p, r, f = p1f.metrics(oof.true_boundary, pred)
        sweep.append((float(t), f))
    threshold, oof_f1 = sorted(sweep, key=lambda x: (x[1], x[0]), reverse=True)[0]

    final_model = make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=1000, random_state=p1f.RANDOM_STATE))
    final_model.fit(train[feature_columns], train.true_boundary)

    return {'model': final_model, 'threshold': threshold, 'oof_f1': oof_f1, 'feature_columns': feature_columns, 'vocab': vocab}


def verify_frozen_reproduction(fit):
    ok_threshold = abs(fit['threshold'] - EXPECTED_THRESHOLD) < 1e-9
    ok_f1 = abs(fit['oof_f1'] - EXPECTED_OOF_F1) < 1e-6
    if not (ok_threshold and ok_f1):
        raise RuntimeError(
            f"Frozen reproduction mismatch: threshold={fit['threshold']} (expected {EXPECTED_THRESHOLD}), "
            f"oof_f1={fit['oof_f1']} (expected {EXPECTED_OOF_F1}). Refusing to apply to Dataset B."
        )
    print(f"Frozen Phase 1F.5 reproduction verified: threshold={fit['threshold']}, training_oof_f1={fit['oof_f1']:.6f}")


def load_events_b():
    """Mirrors p1f.load_events exactly, minus true_boundary/execution_id -- Dataset B has no GT."""
    e = pd.read_parquet(ROOT / 'outputs/tables/dataset_b_events.parquet')
    e = e.sort_values(['session_id', 'timestamp_ms', 'raw_line_number']).reset_index(drop=True)
    e['event_index'] = e.groupby('session_id').cumcount()
    prev = e.groupby('session_id').shift()
    e['gap_seconds'] = ((e.timestamp_ms - prev.timestamp_ms) / 1000).clip(0, 120).fillna(0)
    e['has_previous_event'] = prev.event_type.notna()
    e['interaction_change'] = e.has_previous_event & e.event_type.ne(prev.event_type)
    e['app_change'] = p1f.changed(e.active_app, prev.active_app)
    e['window_change'] = p1f.changed(e.window_title, prev.window_title)
    e['browser_context_change'] = p1f.changed(e.browser_url, prev.browser_url) | p1f.changed(e.browser_tab_id, prev.browser_tab_id)
    e['chunk_change'] = e.chunk_id.ne(prev.chunk_id) & prev.chunk_id.notna()
    return e


def apply_frozen_pipeline_to_b(fit):
    e = load_events_b()
    e['candidate'] = p1f.candidate_mask(e)
    e['tooling_context'] = p1f3.compute_tooling_context(e)
    vocab = fit['vocab']  # frozen vocabulary from Dataset A, NOT recomputed from B

    base = pd.concat([p1f.session_features(g, vocab) for _, g in e.groupby('session_id', sort=False)], ignore_index=True)
    content = pd.concat([p1f4.session_content_features(g) for _, g in e.groupby('session_id', sort=False)], ignore_index=True)
    candidates = base.merge(content, on='row_id', how='left')
    candidates['tooling_context'] = e.loc[candidates.row_id, 'tooling_context'].to_numpy()

    feature_columns = fit['feature_columns']
    candidates['score'] = fit['model'].predict_proba(candidates[feature_columns])[:, 1]
    picked = p1f3.cluster_boundaries(candidates, fit['threshold'])
    candidates['predicted_boundary'] = candidates.row_id.isin(picked).astype(int)
    return e, candidates, picked


def build_segments_b(e, picked):
    """Same segment-construction logic as p1f.build_segments, minus GT-derived fields (Dataset B
    has no execution_id to report gt_execution_count/gt_primary_execution_id against)."""
    segments = []
    for sid, s in e.groupby('session_id', sort=False):
        cuts = sorted(set(s.index) & picked)
        starts = [s.index[0]] + cuts
        ends = [i - 1 for i in cuts] + [s.index[-1]]
        for n, (a, z) in enumerate(zip(starts, ends), start=1):
            x = s.loc[a:z]
            crosses_chunk = x.chunk_id.nunique() > 1
            segments.append({
                'segment_id': f'{sid}::seg{n:03d}',
                'session_id': sid, 'segment_number': n,
                'start_timestamp': x.timestamp_iso.iloc[0], 'end_timestamp': x.timestamp_iso.iloc[-1],
                'duration_seconds': max(0.0, (x.timestamp_ms.iloc[-1] - x.timestamp_ms.iloc[0]) / 1000),
                'event_count': len(x),
                'start_event_id': x.event_id.iloc[0], 'end_event_id': x.event_id.iloc[-1],
                'start_chunk_id': x.chunk_id.iloc[0], 'end_chunk_id': x.chunk_id.iloc[-1],
                'crosses_chunk': bool(crosses_chunk),
                'handling': 'continuation_across_chunk' if crosses_chunk else 'within_chunk',
                'start_row': int(a), 'end_row': int(z),
            })
    return pd.DataFrame(segments)


def main():
    fit = fit_frozen_pipeline_on_dataset_a()
    verify_frozen_reproduction(fit)

    e, candidates, picked = apply_frozen_pipeline_to_b(fit)
    segments = build_segments_b(e, picked)
    segments.to_csv(OUT / 'raw_segments.csv', index=False)

    candidates.to_csv(OUT / 'candidate_scores.csv', index=False)

    summary = {
        'frozen_threshold': fit['threshold'],
        'frozen_training_oof_f1': fit['oof_f1'],
        'dataset_b_events': int(len(e)),
        'dataset_b_sessions': int(e.session_id.nunique()),
        'dataset_b_candidates': int(len(candidates)),
        'dataset_b_predicted_boundaries': int(len(picked)),
        'dataset_b_segments': int(len(segments)),
        'segments_crossing_chunk': int(segments.crosses_chunk.sum()),
        'median_segment_duration_seconds': float(segments.duration_seconds.median()),
        'mean_segment_duration_seconds': float(segments.duration_seconds.mean()),
        'segments_per_session': segments.groupby('session_id').size().to_dict(),
    }
    (OUT / 'phase2a_run_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return e, candidates, segments


if __name__ == '__main__':
    main()
