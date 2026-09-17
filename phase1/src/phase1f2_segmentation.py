"""Phase 1F.2: same Phase 1F scorer, better post-processing.

The Phase 1F.1 error diagnosis (`phase1f1_error_diagnosis/README.md`) found two concrete,
non-semantic causes behind most of Phase 1F's remaining error:

1. ~61% of missed boundaries (330/542) already scored above the 0.83 threshold but were
   discarded by greedy 3-event non-maximum suppression, because real switches often produce a
   *burst* of 2-3 near-identical high-scoring candidates within a few events of each other (same
   app, same window, same event-type pattern) -- NMS keeps two neighbors and drops the actual
   GT-labeled event in between, turning one real transition into one FN and two FPs at once.
2. ~34% of confident false positives were nowhere near any true boundary; inspected examples were
   GT-unassigned background/tooling activity (the recording agent's own UI, admin PowerShell,
   session teardown) that behaviorally mimics a process switch but isn't business work at all.

This script reuses the Phase 1F feature engineering, candidate generation, and model training
UNCHANGED (imported from `phase1f_segmentation.py`, not reimplemented) and only changes what
happens after scoring:

- `select_boundaries` (greedy pairwise NMS) is replaced by `cluster_boundaries`: candidates within
  `MIN_EVENT_GAP` events of each other, chained transitively, are grouped into one cluster and
  only the single highest-scoring candidate in each cluster is kept. This directly targets the
  burst mechanism above -- a 751/753/754-style burst becomes one cluster with one representative,
  not three separate outcomes.
- A conservative, GT-free, schema-driven "tooling/background" filter removes candidates that are
  the recording agent's own UI, common OS/admin tooling (PowerShell, cmd, Task Manager), or within
  two events of a SYSTEM-layer lifecycle event (session_start/end, upload_*, extension_*), before
  they can ever be selected as a boundary. It never touches the model or its features -- it only
  disqualifies candidates from the post-scoring selection step.

No feature, no model architecture, no LLM, no Dataset B.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import phase1f_segmentation as p1f

ROOT = p1f.ROOT
OUT = ROOT / 'phase1' / 'results' / 'phase1f2_segmentation'
PLOTS = OUT / 'plots'
OUT.mkdir(exist_ok=True)
PLOTS.mkdir(exist_ok=True)

CLUSTER_GAP = p1f.MIN_EVENT_GAP  # same distance parameter as the old NMS, only the algorithm changes
TOOLING_PROXIMITY_EVENTS = 2
TOOLING_APP_KEYWORDS = ['procmine', 'powershell', 'cmd.exe', 'command prompt', 'task manager']
SYSTEM_LIFECYCLE_EVENTS = {
    'session_start', 'session_end', 'upload_started', 'upload_completed', 'upload_failed',
    'extension_connected', 'extension_disconnected',
}


def compute_tooling_context(e):
    """Conservative, GT-free flag: is this event plausibly non-business tooling/background
    activity, rather than user business work? Uses only generically observable signals (app
    name, event layer/type, proximity to agent lifecycle events) so it is not overfit to
    Dataset A's specific business applications and should carry over to Dataset B."""
    app = e.active_app.fillna('').str.lower()
    process = e.process_name.fillna('').str.lower()
    keyword_hit = pd.Series(False, index=e.index)
    for kw in TOOLING_APP_KEYWORDS:
        keyword_hit = keyword_hit | app.str.contains(kw, regex=False) | process.str.contains(kw, regex=False)

    is_lifecycle_event = e.layer.eq('SYSTEM') | e.event_type.isin(SYSTEM_LIFECYCLE_EVENTS)
    near_lifecycle = is_lifecycle_event.copy()
    grouped_layer = e.groupby('session_id').layer
    grouped_event = e.groupby('session_id').event_type
    for k in range(1, TOOLING_PROXIMITY_EVENTS + 1):
        for shift in (k, -k):
            near_lifecycle = (
                near_lifecycle
                | grouped_layer.shift(shift).eq('SYSTEM').fillna(False)
                | grouped_event.shift(shift).isin(SYSTEM_LIFECYCLE_EVENTS).fillna(False)
            )
    return keyword_hit | near_lifecycle


def cluster_boundaries(df, threshold, max_gap=CLUSTER_GAP):
    """Replace greedy pairwise NMS with chain clustering: candidates whose event_index gap to
    the previous eligible candidate (in the same session) is <= max_gap join the same cluster,
    transitively, so a burst of 3 candidates spanning 3 events becomes ONE cluster instead of
    silently keeping two of the three. Only the highest-scoring candidate per cluster survives.
    Tooling-flagged candidates are dropped before clustering and can never be selected."""
    eligible = df[(df.score >= threshold) & (~df.tooling_context)]
    picked = []
    for _, g in eligible.groupby('session_id', sort=False):
        g = g.sort_values('event_index')
        idx = g.event_index.to_numpy()
        row_ids = g.row_id.to_numpy()
        scores = g.score.to_numpy()
        cluster_id = np.zeros(len(idx), dtype=int)
        for i in range(1, len(idx)):
            cluster_id[i] = cluster_id[i - 1] + (1 if idx[i] - idx[i - 1] > max_gap else 0)
        for c in np.unique(cluster_id):
            members = np.where(cluster_id == c)[0]
            best = members[np.argmax(scores[members])]
            picked.append(row_ids[best])
    return set(picked)


def build_boundary_results(e, candidates, heldout_sessions):
    candidates = candidates.copy()
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
    return pd.concat([candidates, missed_rows], ignore_index=True, sort=False).sort_values(['session_id', 'event_index'])


def save_plots(calibration, segments):
    fig, ax = plt.subplots()
    ax.plot(calibration.threshold, calibration.precision, label='precision')
    ax.plot(calibration.threshold, calibration.recall, label='recall')
    ax.plot(calibration.threshold, calibration.f1, label='f1')
    ax.set_xlabel('threshold'); ax.set_ylabel('score'); ax.set_title('Phase 1F.2 training OOF calibration sweep'); ax.legend()
    fig.tight_layout(); fig.savefig(PLOTS / 'calibration_curve.png', dpi=160); plt.close(fig)

    fig, ax = plt.subplots()
    clip_at = segments.duration_seconds.quantile(0.99) or 1.0
    ax.hist(segments.duration_seconds.clip(upper=clip_at), bins=40)
    ax.set_xlabel('segment duration (seconds, 99th pct clipped)'); ax.set_ylabel('segment count')
    ax.set_title('Phase 1F.2 predicted segment duration distribution')
    fig.tight_layout(); fig.savefig(PLOTS / 'segment_duration_distribution.png', dpi=160); plt.close(fig)


def main():
    # Identical candidate generation and feature engineering to Phase 1F -- imported, not reimplemented.
    e = p1f.load_events()
    e['candidate'] = p1f.candidate_mask(e)
    e['tooling_context'] = compute_tooling_context(e)
    vocab = e.event_type.value_counts().head(p1f.VOCAB_SIZE).index.tolist()

    candidates = pd.concat(
        [p1f.session_features(g, vocab) for _, g in e.groupby('session_id', sort=False)],
        ignore_index=True,
    )
    candidates['true_boundary'] = e.loc[candidates.row_id, 'true_boundary'].to_numpy()
    candidates['gt_execution_id'] = e.loc[candidates.row_id, 'execution_id'].to_numpy()
    candidates['tooling_context'] = e.loc[candidates.row_id, 'tooling_context'].to_numpy()

    session_ids = sorted(e.session_id.unique())
    heldout_sessions = set(session_ids[::p1f.HOLDOUT_STRIDE])
    train = candidates[~candidates.session_id.isin(heldout_sessions)].copy()

    # Same feature set as Phase 1F, plus excluding the new tooling_context flag (post-processing
    # only -- it must never reach the model).
    exclude = p1f.NON_FEATURE_COLUMNS | {'tooling_context'}
    feature_columns = [c for c in candidates.columns if c not in exclude and candidates[c].dtype != object]
    assert feature_columns == [c for c in candidates.columns if c not in p1f.NON_FEATURE_COLUMNS and c != 'tooling_context' and candidates[c].dtype != object]

    # Same model, same training procedure, same random_state as Phase 1F.
    oof_rows = []
    for train_idx, val_idx in GroupKFold(n_splits=5).split(train, train.true_boundary, groups=train.session_id):
        fold_model = make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=1000, random_state=p1f.RANDOM_STATE))
        fold_model.fit(train.iloc[train_idx][feature_columns], train.iloc[train_idx].true_boundary)
        fold_val = train.iloc[val_idx].copy()
        fold_val['score'] = fold_model.predict_proba(fold_val[feature_columns])[:, 1]
        oof_rows.append(fold_val)
    oof = pd.concat(oof_rows, ignore_index=True)

    # Threshold recalibrated for the NEW selection procedure (clustering + tooling filter), using
    # the same training-only OOF search as Phase 1F -- the selection method changed, so the
    # threshold that's optimal for it must be re-found the same documented way, not reused blindly.
    sweep = []
    for t in np.round(np.arange(0.05, 0.951, 0.01), 2):
        pred = oof.row_id.isin(cluster_boundaries(oof, float(t))).astype(int)
        p, r, f = p1f.metrics(oof.true_boundary, pred)
        sweep.append({'threshold': float(t), 'precision': p, 'recall': r, 'f1': f, 'predicted_boundaries': int(pred.sum())})
    calibration = pd.DataFrame(sweep)
    calibration.to_csv(OUT / 'calibration_curve.csv', index=False)
    best = calibration.sort_values(['f1', 'threshold'], ascending=[False, False]).iloc[0]
    threshold = float(best.threshold)

    final_model = make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=1000, random_state=p1f.RANDOM_STATE))
    final_model.fit(train[feature_columns], train.true_boundary)
    candidates['score'] = final_model.predict_proba(candidates[feature_columns])[:, 1]
    picked = cluster_boundaries(candidates, threshold)
    candidates['predicted_boundary'] = candidates.row_id.isin(picked).astype(int)

    boundary_results = build_boundary_results(e, candidates, heldout_sessions)
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

    # Diagnostic-relevant extras: how much did the tooling filter actually remove, and how many
    # of Phase 1F's specific NMS-suppressed misses (score >= 0.83 there) are recovered now?
    scored_candidates = candidates[candidates.score.notna()]
    tooling_flagged = int(scored_candidates.tooling_context.sum())
    tooling_true_boundary_loss = int(scored_candidates[scored_candidates.tooling_context].true_boundary.sum())
    tooling_would_have_been_selected = int(
        scored_candidates[(scored_candidates.tooling_context) & (scored_candidates.score >= threshold)].shape[0]
    )

    old_boundary_results = pd.read_csv(ROOT / 'phase1' / 'results' / 'phase1f_segmentation' / 'boundary_results.csv', usecols=['row_id', 'result', 'score'])
    old_nms_suppressed = set(old_boundary_results[(old_boundary_results.result == 'FN_candidate') & (old_boundary_results.score >= 0.83)].row_id)
    new_result_by_row = boundary_results.set_index('row_id').result
    recovered = int(sum(new_result_by_row.get(rid, 'FN_not_candidate') == 'TP' for rid in old_nms_suppressed))

    summary = {
        'threshold': threshold,
        'training_oof_f1': float(best.f1),
        'candidate_pool_size': int(len(candidates)),
        'tooling_flagged_candidates': tooling_flagged,
        'tooling_flagged_true_boundaries_lost': tooling_true_boundary_loss,
        'tooling_flagged_candidates_that_would_have_cleared_threshold': tooling_would_have_been_selected,
        'phase1f_nms_suppressed_fn_count': len(old_nms_suppressed),
        'phase1f_nms_suppressed_fn_now_recovered_as_tp': recovered,
        'heldout': {row.metric: row.value for _, row in stats[stats.scope == 'heldout'].iterrows()},
        'all_dataset_a': {row.metric: row.value for _, row in stats[stats.scope == 'all_dataset_a'].iterrows()},
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    main()
