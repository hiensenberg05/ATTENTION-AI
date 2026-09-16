"""Phase 1F.5: controlled combination of the two independent wins found so far.

Phase 1F.3 (clustering + earliest-event representative, `phase1f3_segmentation/README.md`) fixed
most of the NMS burst-suppression problem but still trailed the Phase 1F baseline on exact-match
recall (0.322 vs 0.368 held-out F1). Phase 1F.4 (case-ID content features,
`phase1f4_segmentation/README.md`) gave a small, real, consistent improvement over the baseline
(0.376 held-out F1) by adding four features derived from extracted_text/clipboard_text. The two
changes are in different parts of the pipeline (scorer input vs. post-scoring selection) and
address different error sources (content-invisible switches vs. burst fragmentation), so this
combines them to see whether the effects stack.

Composition, nothing else:
- Candidate generation, feature engineering: Phase 1F, unchanged (imported).
- Scorer input: Phase 1F's features PLUS Phase 1F.4's four case-ID features, unchanged
  (imported from phase1f4_segmentation.session_content_features).
- Post-processing: Phase 1F.3's tooling filter + chain clustering with earliest-event
  representative, unchanged (imported from phase1f3_segmentation).
- Model architecture/hyperparameters/training procedure: identical to Phase 1F throughout.

No new features, no embeddings, no LLM, no Dataset B.
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import phase1f_segmentation as p1f
import phase1f2_segmentation as p1f2
import phase1f3_segmentation as p1f3
import phase1f4_segmentation as p1f4

ROOT = p1f.ROOT
OUT = ROOT / 'phase1f5_segmentation'
PLOTS = OUT / 'plots'
OUT.mkdir(exist_ok=True)
PLOTS.mkdir(exist_ok=True)

NEW_CONTENT_FEATURES = ['pre_has_case_id', 'post_has_case_id', 'case_id_changed', 'case_id_persists']


def save_plots(calibration, segments):
    fig, ax = plt.subplots()
    ax.plot(calibration.threshold, calibration.precision, label='precision')
    ax.plot(calibration.threshold, calibration.recall, label='recall')
    ax.plot(calibration.threshold, calibration.f1, label='f1')
    ax.set_xlabel('threshold'); ax.set_ylabel('score'); ax.set_title('Phase 1F.5 training OOF calibration sweep'); ax.legend()
    fig.tight_layout(); fig.savefig(PLOTS / 'calibration_curve.png', dpi=160); plt.close(fig)

    fig, ax = plt.subplots()
    clip_at = segments.duration_seconds.quantile(0.99) or 1.0
    ax.hist(segments.duration_seconds.clip(upper=clip_at), bins=40)
    ax.set_xlabel('segment duration (seconds, 99th pct clipped)'); ax.set_ylabel('segment count')
    ax.set_title('Phase 1F.5 predicted segment duration distribution')
    fig.tight_layout(); fig.savefig(PLOTS / 'segment_duration_distribution.png', dpi=160); plt.close(fig)


def main():
    # Candidate generation + base features: Phase 1F, unchanged.
    e = p1f.load_events()
    e['candidate'] = p1f.candidate_mask(e)
    # Tooling filter: Phase 1F.3, unchanged.
    e['tooling_context'] = p1f3.compute_tooling_context(e)
    vocab = e.event_type.value_counts().head(p1f.VOCAB_SIZE).index.tolist()

    base = pd.concat([p1f.session_features(g, vocab) for _, g in e.groupby('session_id', sort=False)], ignore_index=True)
    # Content features: Phase 1F.4, unchanged.
    content = pd.concat([p1f4.session_content_features(g) for _, g in e.groupby('session_id', sort=False)], ignore_index=True)
    candidates = base.merge(content, on='row_id', how='left')
    candidates['true_boundary'] = e.loc[candidates.row_id, 'true_boundary'].to_numpy()
    candidates['gt_execution_id'] = e.loc[candidates.row_id, 'execution_id'].to_numpy()
    candidates['tooling_context'] = e.loc[candidates.row_id, 'tooling_context'].to_numpy()

    session_ids = sorted(e.session_id.unique())
    heldout_sessions = set(session_ids[::p1f.HOLDOUT_STRIDE])
    train = candidates[~candidates.session_id.isin(heldout_sessions)].copy()

    # Same feature set as 1F.4 (base + content features), same exclusion rule as 1F.2/1F.3 for
    # the post-processing-only tooling_context flag.
    exclude = p1f.NON_FEATURE_COLUMNS | {'tooling_context'}
    feature_columns = [c for c in candidates.columns if c not in exclude and candidates[c].dtype != object]
    assert set(NEW_CONTENT_FEATURES).issubset(feature_columns), 'content features must reach the scorer'

    oof_rows = []
    for train_idx, val_idx in GroupKFold(n_splits=5).split(train, train.true_boundary, groups=train.session_id):
        fold_model = make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=1000, random_state=p1f.RANDOM_STATE))
        fold_model.fit(train.iloc[train_idx][feature_columns], train.iloc[train_idx].true_boundary)
        fold_val = train.iloc[val_idx].copy()
        fold_val['score'] = fold_model.predict_proba(fold_val[feature_columns])[:, 1]
        oof_rows.append(fold_val)
    oof = pd.concat(oof_rows, ignore_index=True)

    # Selection: Phase 1F.3's clustering + earliest-event representative, unchanged. Threshold
    # recalibrated for this exact selection procedure via the same training-only OOF search used
    # throughout the Phase 1F family.
    sweep = []
    for t in np.round(np.arange(0.05, 0.951, 0.01), 2):
        pred = oof.row_id.isin(p1f3.cluster_boundaries(oof, float(t))).astype(int)
        p, r, f = p1f.metrics(oof.true_boundary, pred)
        sweep.append({'threshold': float(t), 'precision': p, 'recall': r, 'f1': f, 'predicted_boundaries': int(pred.sum())})
    calibration = pd.DataFrame(sweep)
    calibration.to_csv(OUT / 'calibration_curve.csv', index=False)
    best = calibration.sort_values(['f1', 'threshold'], ascending=[False, False]).iloc[0]
    threshold = float(best.threshold)

    final_model = make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=1000, random_state=p1f.RANDOM_STATE))
    final_model.fit(train[feature_columns], train.true_boundary)
    candidates['score'] = final_model.predict_proba(candidates[feature_columns])[:, 1]
    picked = p1f3.cluster_boundaries(candidates, threshold)
    candidates['predicted_boundary'] = candidates.row_id.isin(picked).astype(int)

    boundary_results = p1f2.build_boundary_results(e, candidates, heldout_sessions)
    boundary_results.to_csv(OUT / 'boundary_results.csv', index=False)

    segments = p1f.build_segments(e, picked)
    segments.to_csv(OUT / 'segment_results.csv', index=False)

    stats, session_stats = p1f.compute_statistics(boundary_results, segments)
    stats.to_csv(OUT / 'segmentation_statistics.csv', index=False)
    session_stats.to_csv(OUT / 'session_results.csv', index=False)

    p1f.build_examples(e, boundary_results).to_csv(OUT / 'boundary_examples.csv', index=False)

    weights = pd.DataFrame({'feature': feature_columns, 'coefficient': final_model[-1].coef_[0]})
    weights.sort_values('coefficient', key=np.abs, ascending=False).head(20).to_csv(OUT / 'scorer_feature_weights.csv', index=False)

    save_plots(calibration, segments)

    old_boundary_results = pd.read_csv(ROOT / 'phase1f_segmentation' / 'boundary_results.csv', usecols=['row_id', 'result', 'score'])
    old_nms_suppressed = set(old_boundary_results[(old_boundary_results.result == 'FN_candidate') & (old_boundary_results.score >= 0.83)].row_id)
    new_result_by_row = boundary_results.set_index('row_id').result
    recovered = int(sum(new_result_by_row.get(rid, 'FN_not_candidate') == 'TP' for rid in old_nms_suppressed))

    summary = {
        'threshold': threshold,
        'training_oof_f1': float(best.f1),
        'candidate_pool_size': int(len(candidates)),
        'phase1f_nms_suppressed_fn_count': len(old_nms_suppressed),
        'phase1f_nms_suppressed_fn_now_recovered_as_tp': recovered,
        'heldout': {row.metric: row.value for _, row in stats[stats.scope == 'heldout'].iterrows()},
        'all_dataset_a': {row.metric: row.value for _, row in stats[stats.scope == 'all_dataset_a'].iterrows()},
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    main()
