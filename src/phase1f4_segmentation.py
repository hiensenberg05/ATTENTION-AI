"""Phase 1F.4: same Phase 1F post-processing (original NMS), scorer gets new content features.

The follow-up investigation (not in this repo as a script -- done interactively) into
`extracted_text`/`clipboard_text` availability found:

- Coverage is higher near real boundaries than the flat 4.48% dataset average suggests: 14.4%
  within +/-2 events of a true boundary, and 33.1% of all true boundaries (458/1382) have text on
  BOTH sides of the model's +/-20 event window.
- When present, the content is genuinely case-identifying, not generic UI noise: real samples
  contain literal case IDs with status, e.g. "SUP-110019-004: ...completed", "INV-071644-001:
  ...approved". A simple regex (`[A-Z]{2,5}-\\d{4,10}(-\\d{2,4})?`) reliably extracts these.
- Of the 327 true boundaries where such an ID is extractable on both sides, only 101 (31%) show a
  DIFFERENT id pre-to-post; 226 (69%) show the SAME id -- meaning many GT boundaries are a
  process-type switch on the same case, not a case-to-case switch. So this feature is real but
  partial: it can only directly help a minority of boundaries, not close the whole gap.
- `clipboard_text` is 0% populated in all of Dataset A (dead weight, included anyway for
  Dataset-B generality since the code should not assume that stays true).

This script keeps Phase 1F's post-processing UNCHANGED (imports and reuses the original greedy
`select_boundaries` NMS, not 1F.2/1F.3's clustering) so the effect of adding content features can
be measured in isolation, against the Phase 1F baseline, without confounding it with the
post-processing experiments. It adds four new candidate-level features derived only from
`extracted_text`/`clipboard_text` in the same +/-20 event windows already used by every other
feature (`pre_has_case_id`, `post_has_case_id`, `case_id_changed`, `case_id_persists`), retrains
the same LogisticRegression pipeline with the same procedure, and reruns the same evaluation.

No GT identity used (this is OCR'd screen text, not ground truth), no post-processing change, no
LLM, no Dataset B.
"""
from pathlib import Path
import json
import re

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

ROOT = p1f.ROOT
OUT = ROOT / 'phase1f4_segmentation'
PLOTS = OUT / 'plots'
OUT.mkdir(exist_ok=True)
PLOTS.mkdir(exist_ok=True)

CASE_ID_RE = re.compile(r'\b([A-Z]{2,5}-\d{4,10}(?:-\d{2,4})?)\b')


def extract_case_ids(text):
    if not isinstance(text, str) or not text:
        return frozenset()
    return frozenset(CASE_ID_RE.findall(text))


def session_content_features(session_events):
    """Same +/-WINDOW pre/post windows as p1f.session_features, but only for the case-ID
    presence/overlap signal -- computed separately and merged by row_id so the existing feature
    code doesn't need to be touched."""
    s = session_events.reset_index().rename(columns={'index': 'row_id'})
    n = len(s)
    text_source = s.extracted_text.combine_first(s.clipboard_text).to_numpy(dtype=object)
    ids_per_event = [extract_case_ids(t) for t in text_source]

    positions = np.flatnonzero(s.candidate.to_numpy())
    rows = []
    for i in positions:
        pre_lo, pre_hi = max(0, i - p1f.WINDOW), i
        post_lo, post_hi = i, min(n, i + p1f.WINDOW)
        pre_ids = frozenset().union(*ids_per_event[pre_lo:pre_hi]) if pre_hi > pre_lo else frozenset()
        post_ids = frozenset().union(*ids_per_event[post_lo:post_hi]) if post_hi > post_lo else frozenset()
        both_present = bool(pre_ids) and bool(post_ids)
        rows.append({
            'row_id': int(s.row_id.iat[i]),
            'pre_has_case_id': int(bool(pre_ids)),
            'post_has_case_id': int(bool(post_ids)),
            'case_id_changed': int(both_present and pre_ids.isdisjoint(post_ids)),
            'case_id_persists': int(both_present and not pre_ids.isdisjoint(post_ids)),
        })
    return pd.DataFrame(rows)


def save_plots(calibration, segments):
    fig, ax = plt.subplots()
    ax.plot(calibration.threshold, calibration.precision, label='precision')
    ax.plot(calibration.threshold, calibration.recall, label='recall')
    ax.plot(calibration.threshold, calibration.f1, label='f1')
    ax.set_xlabel('threshold'); ax.set_ylabel('score'); ax.set_title('Phase 1F.4 training OOF calibration sweep'); ax.legend()
    fig.tight_layout(); fig.savefig(PLOTS / 'calibration_curve.png', dpi=160); plt.close(fig)

    fig, ax = plt.subplots()
    clip_at = segments.duration_seconds.quantile(0.99) or 1.0
    ax.hist(segments.duration_seconds.clip(upper=clip_at), bins=40)
    ax.set_xlabel('segment duration (seconds, 99th pct clipped)'); ax.set_ylabel('segment count')
    ax.set_title('Phase 1F.4 predicted segment duration distribution')
    fig.tight_layout(); fig.savefig(PLOTS / 'segment_duration_distribution.png', dpi=160); plt.close(fig)


def main():
    e = p1f.load_events()
    e['candidate'] = p1f.candidate_mask(e)
    vocab = e.event_type.value_counts().head(p1f.VOCAB_SIZE).index.tolist()

    base = pd.concat([p1f.session_features(g, vocab) for _, g in e.groupby('session_id', sort=False)], ignore_index=True)
    content = pd.concat([session_content_features(g) for _, g in e.groupby('session_id', sort=False)], ignore_index=True)
    candidates = base.merge(content, on='row_id', how='left')
    candidates['true_boundary'] = e.loc[candidates.row_id, 'true_boundary'].to_numpy()
    candidates['gt_execution_id'] = e.loc[candidates.row_id, 'execution_id'].to_numpy()

    new_feature_columns = ['pre_has_case_id', 'post_has_case_id', 'case_id_changed', 'case_id_persists']
    print('new content feature prevalence (share of all candidates):')
    print(candidates[new_feature_columns].mean().to_string())
    print('new content feature prevalence among true boundaries only:')
    print(candidates.loc[candidates.true_boundary == 1, new_feature_columns].mean().to_string())

    session_ids = sorted(e.session_id.unique())
    heldout_sessions = set(session_ids[::p1f.HOLDOUT_STRIDE])
    train = candidates[~candidates.session_id.isin(heldout_sessions)].copy()

    # Same exclusion rule as Phase 1F, the new content columns fall through into feature_columns
    # automatically since they're int dtype and not in NON_FEATURE_COLUMNS -- that's the point.
    feature_columns = [c for c in candidates.columns if c not in p1f.NON_FEATURE_COLUMNS and candidates[c].dtype != object]

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
        pred = oof.row_id.isin(p1f.select_boundaries(oof, float(t))).astype(int)
        p, r, f = p1f.metrics(oof.true_boundary, pred)
        sweep.append({'threshold': float(t), 'precision': p, 'recall': r, 'f1': f, 'predicted_boundaries': int(pred.sum())})
    calibration = pd.DataFrame(sweep)
    calibration.to_csv(OUT / 'calibration_curve.csv', index=False)
    best = calibration.sort_values(['f1', 'threshold'], ascending=[False, False]).iloc[0]
    threshold = float(best.threshold)

    final_model = make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=1000, random_state=p1f.RANDOM_STATE))
    final_model.fit(train[feature_columns], train.true_boundary)
    candidates['score'] = final_model.predict_proba(candidates[feature_columns])[:, 1]
    picked = p1f.select_boundaries(candidates, threshold)
    candidates['predicted_boundary'] = candidates.row_id.isin(picked).astype(int)
    candidates['split'] = np.where(candidates.session_id.isin(heldout_sessions), 'heldout', 'training')
    candidates['result'] = np.select(
        [
            (candidates.true_boundary == 1) & (candidates.predicted_boundary == 1),
            (candidates.true_boundary == 0) & (candidates.predicted_boundary == 1),
            candidates.true_boundary == 1,
        ],
        ['TP', 'FP', 'FN_candidate'], default='TN',
    )
    missed = e[(e.true_boundary == 1) & ~e.index.isin(candidates.row_id)]
    missed_rows = pd.DataFrame({
        'row_id': missed.index, 'session_id': missed.session_id, 'timestamp_iso': missed.timestamp_iso,
        'event_index': missed.event_index, 'true_boundary': 1, 'score': np.nan, 'predicted_boundary': 0,
        'split': np.where(missed.session_id.isin(heldout_sessions), 'heldout', 'training'),
        'result': 'FN_not_candidate',
    })
    boundary_results = pd.concat([candidates, missed_rows], ignore_index=True, sort=False).sort_values(['session_id', 'event_index'])
    boundary_results.to_csv(OUT / 'boundary_results.csv', index=False)

    segments = p1f.build_segments(e, picked)
    segments.to_csv(OUT / 'segment_results.csv', index=False)

    stats, session_stats = p1f.compute_statistics(boundary_results, segments)
    stats.to_csv(OUT / 'segmentation_statistics.csv', index=False)
    session_stats.to_csv(OUT / 'session_results.csv', index=False)

    p1f.build_examples(e, boundary_results).to_csv(OUT / 'boundary_examples.csv', index=False)

    weights = pd.DataFrame({'feature': feature_columns, 'coefficient': final_model[-1].coef_[0]})
    weights = weights.sort_values('coefficient', key=np.abs, ascending=False)
    weights.head(20).to_csv(OUT / 'scorer_feature_weights.csv', index=False)
    content_weight_rows = weights[weights.feature.isin(new_feature_columns)]

    save_plots(calibration, segments)

    summary = {
        'threshold': threshold,
        'training_oof_f1': float(best.f1),
        'candidate_pool_size': int(len(candidates)),
        'content_feature_coefficients': dict(zip(content_weight_rows.feature, content_weight_rows.coefficient.round(4))),
        'heldout': {row.metric: row.value for _, row in stats[stats.scope == 'heldout'].iterrows()},
        'all_dataset_a': {row.metric: row.value for _, row in stats[stats.scope == 'all_dataset_a'].iterrows()},
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    main()
