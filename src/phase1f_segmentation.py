"""Phase 1F: high-recall candidate generation + contextual scoring -> Dataset A segmentation.

Rewrite of the original Phase 1F draft. That draft was never executed (no outputs existed
anywhere in the repo) and, on inspection, its non-maximum suppression step compared event
positions across different sessions, so boundaries in unrelated sessions could suppress each
other. This version fixes that and is actually run to produce real metrics.

Same two-stage design validated across Phases 1B-1E: keep high-recall candidate generation and
the boundary decision as separate problems, never give the scorer GT process identity (code,
name, variant, domain, case_id), and pick the decision threshold only from training-session
out-of-fold predictions, never from the held-out sessions.
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'phase1f_segmentation'
PLOTS = OUT / 'plots'
OUT.mkdir(exist_ok=True)
PLOTS.mkdir(exist_ok=True)

WINDOW = 20                  # events considered on each side of a candidate transition
MIN_EVENT_GAP = 3            # minimum event-index separation between two accepted cuts, same session
GAP_CANDIDATE_SECONDS = 1.0
VOCAB_SIZE = 18
RANDOM_STATE = 41
HOLDOUT_STRIDE = 5            # every Nth sorted session is held out, same convention as Phase 1B/1B.1

ACTIVITY_GROUPS = {
    'keyboard': {'keystroke', 'shortcut', 'text_input_complete'},
    'mouse': {'mouse_click', 'mouse_double_click', 'mouse_scroll', 'mouse_drag_drop'},
    'browser': {'browser_click', 'browser_form_input', 'browser_navigation', 'browser_tab_event', 'browser_alert', 'browser_error'},
    'clipboard': {'clipboard_change'},
}

WINDOW_BASES = [
    'gap_mean', 'gap_max', 'app_switch_rate', 'window_switch_rate', 'browser_context_rate',
    'unique_apps', 'unique_windows', 'unique_tabs', 'text_available_rate',
    'keyboard_rate', 'mouse_rate', 'browser_rate', 'clipboard_rate',
]

NON_FEATURE_COLUMNS = {'row_id', 'session_id', 'timestamp_iso', 'event_index', 'true_boundary', 'gt_execution_id'}


def changed(a, b):
    return a.notna() & b.notna() & a.ne(b)


def metrics(y_true, y_pred):
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, average='binary', zero_division=0)
    return float(p), float(r), float(f)


def load_events():
    e = pd.read_parquet(ROOT / 'outputs/tables/dataset_a_events_with_gt.parquet')
    e = e.sort_values(['session_id', 'timestamp_ms', 'raw_line_number']).reset_index(drop=True)
    e['event_index'] = e.groupby('session_id').cumcount()
    prev = e.groupby('session_id').shift()
    e['gap_seconds'] = ((e.timestamp_ms - prev.timestamp_ms) / 1000).clip(0, 120).fillna(0)
    e['has_previous_event'] = prev.event_type.notna()
    e['interaction_change'] = e.has_previous_event & e.event_type.ne(prev.event_type)
    e['app_change'] = changed(e.active_app, prev.active_app)
    e['window_change'] = changed(e.window_title, prev.window_title)
    e['browser_context_change'] = changed(e.browser_url, prev.browser_url) | changed(e.browser_tab_id, prev.browser_tab_id)
    e['chunk_change'] = e.chunk_id.ne(prev.chunk_id) & prev.chunk_id.notna()
    e['true_boundary'] = (e.execution_id.notna() & prev.execution_id.notna() & e.execution_id.ne(prev.execution_id)).astype(int)
    return e


def candidate_mask(e):
    # Chunk changes are deliberately excluded here: chunks are a recording artifact, not a
    # business-process signal, so they can never generate a candidate on their own.
    weak_signal_event = e.event_type.isin(['clipboard_change', 'browser_navigation', 'browser_form_input'])
    return e.has_previous_event & (
        e.interaction_change | e.app_change | e.window_change | e.browser_context_change
        | (e.gap_seconds > GAP_CANDIDATE_SECONDS) | weak_signal_event
    )


def session_features(session_events, vocab):
    s = session_events.reset_index().rename(columns={'index': 'row_id'})
    n = len(s)

    # Pull every column the window loop needs into plain numpy arrays once per session.
    # Doing this lets the per-candidate loop below use numpy slicing/aggregation instead of
    # pandas .iloc + Series ops, which is what made the first version of this pipeline too
    # slow to finish: with ~100k candidates across Dataset A and ~30 pandas calls each
    # (mean/max/nunique/isin per side), the pandas call overhead alone dominated runtime.
    row_id = s.row_id.to_numpy()
    session_id = s.session_id.to_numpy(dtype=object)
    timestamp_iso = s.timestamp_iso.to_numpy(dtype=object)
    event_index = s.event_index.to_numpy()
    gap = s.gap_seconds.to_numpy(dtype=float)
    interaction_change = s.interaction_change.to_numpy()
    app_change = s.app_change.to_numpy()
    window_change = s.window_change.to_numpy()
    browser_change = s.browser_context_change.to_numpy()
    chunk_change = s.chunk_change.to_numpy()
    event_type = s.event_type.to_numpy(dtype=object)
    active_app = s.active_app.to_numpy(dtype=object)
    window_title = s.window_title.to_numpy(dtype=object)
    browser_tab_id = s.browser_tab_id.to_numpy(dtype=object)
    text_available = (s.extracted_text.notna() | s.clipboard_text.notna()).to_numpy()

    activity_bool = {name: np.isin(event_type, list(types)) for name, types in ACTIVITY_GROUPS.items()}
    vocab_bool = {v: (event_type == v) for v in vocab}

    positions = np.flatnonzero(s.candidate.to_numpy())
    rows = []
    for i in positions:
        row = {
            'row_id': int(row_id[i]), 'session_id': session_id[i], 'timestamp_iso': timestamp_iso[i],
            'event_index': int(event_index[i]), 'gap_seconds': float(gap[i]),
            'interaction_change': int(interaction_change[i]), 'app_change': int(app_change[i]),
            'window_change': int(window_change[i]), 'browser_context_change': int(browser_change[i]),
            'chunk_change': int(chunk_change[i]),
        }
        for side, lo, hi in (('pre', max(0, i - WINDOW), i), ('post', i, min(n, i + WINDOW))):
            width = max(hi - lo, 1)
            empty = hi <= lo
            row[f'{side}_gap_mean'] = float(gap[lo:hi].mean()) if not empty else 0.0
            row[f'{side}_gap_max'] = float(gap[lo:hi].max()) if not empty else 0.0
            row[f'{side}_app_switch_rate'] = float(app_change[lo:hi].mean()) if not empty else 0.0
            row[f'{side}_window_switch_rate'] = float(window_change[lo:hi].mean()) if not empty else 0.0
            row[f'{side}_browser_context_rate'] = float(browser_change[lo:hi].mean()) if not empty else 0.0
            row[f'{side}_unique_apps'] = _nunique(active_app[lo:hi])
            row[f'{side}_unique_windows'] = _nunique(window_title[lo:hi])
            row[f'{side}_unique_tabs'] = _nunique(browser_tab_id[lo:hi])
            row[f'{side}_text_available_rate'] = float(text_available[lo:hi].mean()) if not empty else 0.0
            for name, arr in activity_bool.items():
                row[f'{side}_{name}_rate'] = float(arr[lo:hi].sum() / width)
            for v, arr in vocab_bool.items():
                row[f'{side}_event_{v}'] = float(arr[lo:hi].sum() / width)
        for base in WINDOW_BASES + [f'event_{v}' for v in vocab]:
            row[f'delta_{base}'] = row[f'post_{base}'] - row[f'pre_{base}']
        rows.append(row)
    return pd.DataFrame(rows)


def _nunique(values):
    seen = set()
    for v in values:
        if v is None or (isinstance(v, float) and v != v):
            continue
        seen.add(v)
    return float(len(seen))


def select_boundaries(df, threshold, min_event_gap=MIN_EVENT_GAP):
    """Greedy non-maximum suppression: rank candidates by score, keep the highest-scoring one
    in any cluster, and suppress lower-scoring candidates within `min_event_gap` events of an
    already-accepted cut -- but only within the SAME session. Comparing raw event_index across
    different sessions (as the original draft did) is a bug: session-local event_index values
    collide by coincidence across sessions and would suppress unrelated boundaries."""
    accepted_by_session = {}
    picked = []
    ranked = df[df.score >= threshold].sort_values(['score', 'event_index'], ascending=[False, True])
    for row in ranked.itertuples():
        kept = accepted_by_session.setdefault(row.session_id, [])
        if all(abs(row.event_index - k) >= min_event_gap for k in kept):
            kept.append(row.event_index)
            picked.append(row.row_id)
    return set(picked)


def build_segments(e, picked):
    segments = []
    for sid, s in e.groupby('session_id', sort=False):
        cuts = sorted(set(s.index) & picked)
        starts = [s.index[0]] + cuts
        ends = [i - 1 for i in cuts] + [s.index[-1]]
        for n, (a, z) in enumerate(zip(starts, ends), start=1):
            x = s.loc[a:z]
            crosses_chunk = x.chunk_id.nunique() > 1
            segments.append({
                'session_id': sid, 'segment_number': n,
                'start_timestamp': x.timestamp_iso.iloc[0], 'end_timestamp': x.timestamp_iso.iloc[-1],
                'duration_seconds': max(0.0, (x.timestamp_ms.iloc[-1] - x.timestamp_ms.iloc[0]) / 1000),
                'event_count': len(x),
                'start_chunk_id': x.chunk_id.iloc[0], 'end_chunk_id': x.chunk_id.iloc[-1],
                'crosses_chunk': bool(crosses_chunk),
                'handling': 'continuation_across_chunk' if crosses_chunk else 'within_chunk',
                'gt_execution_count': int(x.execution_id.dropna().nunique()),
                'gt_primary_execution_id': x.execution_id.dropna().mode().iloc[0] if x.execution_id.notna().any() else None,
            })
    return pd.DataFrame(segments)


def compute_statistics(boundary_results, segments):
    stats = []
    for scope, x in [('heldout', boundary_results[boundary_results.split == 'heldout']), ('all_dataset_a', boundary_results)]:
        p, r, f = metrics(x.true_boundary, x.predicted_boundary)
        ss = segments[segments.session_id.isin(x.session_id.unique())]
        gt, pred = int(x.true_boundary.sum()), int(x.predicted_boundary.sum())
        stats += [
            {'scope': scope, 'metric': 'boundary_precision', 'value': p},
            {'scope': scope, 'metric': 'boundary_recall', 'value': r},
            {'scope': scope, 'metric': 'boundary_f1', 'value': f},
            {'scope': scope, 'metric': 'predicted_boundary_count', 'value': pred},
            {'scope': scope, 'metric': 'gt_boundary_count', 'value': gt},
            {'scope': scope, 'metric': 'boundary_count_difference_pred_minus_gt', 'value': pred - gt},
            {'scope': scope, 'metric': 'predicted_segments', 'value': len(ss)},
            {'scope': scope, 'metric': 'median_segment_duration_seconds', 'value': float(ss.duration_seconds.median()) if len(ss) else 0.0},
            {'scope': scope, 'metric': 'mean_segment_duration_seconds', 'value': float(ss.duration_seconds.mean()) if len(ss) else 0.0},
            {'scope': scope, 'metric': 'segments_crossing_chunk', 'value': int(ss.crosses_chunk.sum())},
        ]
    session_rows = []
    for sid, x in boundary_results.groupby('session_id'):
        p, r, f = metrics(x.true_boundary, x.predicted_boundary)
        ss = segments[segments.session_id == sid]
        session_rows.append({
            'session_id': sid, 'split': x.split.iloc[0],
            'gt_boundaries': int(x.true_boundary.sum()), 'predicted_boundaries': int(x.predicted_boundary.sum()),
            'boundary_precision': p, 'boundary_recall': r, 'boundary_f1': f,
            'over_under_segmented': int(x.predicted_boundary.sum() - x.true_boundary.sum()),
            'predicted_segments': len(ss),
            'median_segment_duration_seconds': float(ss.duration_seconds.median()) if len(ss) else 0.0,
            'cross_chunk_segments': int(ss.crosses_chunk.sum()),
        })
    return pd.DataFrame(stats), pd.DataFrame(session_rows)


def context_text(s, idx, side):
    if side == 'pre':
        lo, hi = max(s.index.min(), idx - 8), idx - 1
    else:
        lo, hi = idx, min(s.index.max(), idx + 7)
    x = s.loc[lo:hi]
    text = x.extracted_text.combine_first(x.clipboard_text).dropna()
    return {
        'event_types': ' > '.join(x.event_type.astype(str)),
        'apps': ' > '.join(x.active_app.dropna().astype(str).drop_duplicates().tolist()[:4]),
        'windows': ' > '.join(x.window_title.dropna().astype(str).str[:80].drop_duplicates().tolist()[:3]),
        'text_or_clipboard': str(text.iloc[-1 if side == 'pre' else 0])[:200] if len(text) else '',
    }


def build_examples(e, boundary_results):
    examples = []
    for label in ['TP', 'FP', 'FN_candidate', 'FN_not_candidate']:
        bucket = boundary_results[boundary_results.result == label].sort_values('score', ascending=(label != 'TP')).head(20)
        for _, r in bucket.iterrows():
            s = e[e.session_id == r.session_id]
            pre = context_text(s, int(r.row_id), 'pre')
            post = context_text(s, int(r.row_id), 'post')
            examples.append({
                'result': label, 'session_id': r.session_id, 'timestamp_iso': r.timestamp_iso,
                'score': r.score, 'event_index': r.event_index,
                'pre_event_types': pre['event_types'], 'post_event_types': post['event_types'],
                'pre_apps': pre['apps'], 'post_apps': post['apps'],
                'pre_windows': pre['windows'], 'post_windows': post['windows'],
                'pre_text_or_clipboard': pre['text_or_clipboard'], 'post_text_or_clipboard': post['text_or_clipboard'],
            })
    return pd.DataFrame(examples)


def save_plots(calibration, segments):
    fig, ax = plt.subplots()
    ax.plot(calibration.threshold, calibration.precision, label='precision')
    ax.plot(calibration.threshold, calibration.recall, label='recall')
    ax.plot(calibration.threshold, calibration.f1, label='f1')
    ax.set_xlabel('threshold'); ax.set_ylabel('score'); ax.set_title('Training OOF calibration sweep'); ax.legend()
    fig.tight_layout(); fig.savefig(PLOTS / 'calibration_curve.png', dpi=160); plt.close(fig)

    fig, ax = plt.subplots()
    clip_at = segments.duration_seconds.quantile(0.99) or 1.0
    ax.hist(segments.duration_seconds.clip(upper=clip_at), bins=40)
    ax.set_xlabel('segment duration (seconds, 99th pct clipped)'); ax.set_ylabel('segment count')
    ax.set_title('Predicted segment duration distribution')
    fig.tight_layout(); fig.savefig(PLOTS / 'segment_duration_distribution.png', dpi=160); plt.close(fig)


def main():
    e = load_events()
    e['candidate'] = candidate_mask(e)
    vocab = e.event_type.value_counts().head(VOCAB_SIZE).index.tolist()

    candidates = pd.concat(
        [session_features(g, vocab) for _, g in e.groupby('session_id', sort=False)],
        ignore_index=True,
    )
    candidates['true_boundary'] = e.loc[candidates.row_id, 'true_boundary'].to_numpy()
    candidates['gt_execution_id'] = e.loc[candidates.row_id, 'execution_id'].to_numpy()

    session_ids = sorted(e.session_id.unique())
    heldout_sessions = set(session_ids[::HOLDOUT_STRIDE])
    train = candidates[~candidates.session_id.isin(heldout_sessions)].copy()
    feature_columns = [c for c in candidates.columns if c not in NON_FEATURE_COLUMNS and candidates[c].dtype != object]

    oof_rows = []
    for train_idx, val_idx in GroupKFold(n_splits=5).split(train, train.true_boundary, groups=train.session_id):
        fold_model = make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=1000, random_state=RANDOM_STATE))
        fold_model.fit(train.iloc[train_idx][feature_columns], train.iloc[train_idx].true_boundary)
        fold_val = train.iloc[val_idx].copy()
        fold_val['score'] = fold_model.predict_proba(fold_val[feature_columns])[:, 1]
        oof_rows.append(fold_val)
    oof = pd.concat(oof_rows, ignore_index=True)

    sweep = []
    for t in np.round(np.arange(0.05, 0.951, 0.01), 2):
        pred = oof.row_id.isin(select_boundaries(oof, float(t))).astype(int)
        p, r, f = metrics(oof.true_boundary, pred)
        sweep.append({'threshold': float(t), 'precision': p, 'recall': r, 'f1': f, 'predicted_boundaries': int(pred.sum())})
    calibration = pd.DataFrame(sweep)
    calibration.to_csv(OUT / 'calibration_curve.csv', index=False)
    # Tie-break toward the higher threshold: among equally good F1 scores, prefer the more
    # conservative cut (fewer false positives / over-segmentation).
    best = calibration.sort_values(['f1', 'threshold'], ascending=[False, False]).iloc[0]
    threshold = float(best.threshold)

    final_model = make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=1000, random_state=RANDOM_STATE))
    final_model.fit(train[feature_columns], train.true_boundary)
    candidates['score'] = final_model.predict_proba(candidates[feature_columns])[:, 1]
    picked = select_boundaries(candidates, threshold)
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

    segments = build_segments(e, picked)
    segments.to_csv(OUT / 'segment_results.csv', index=False)

    stats, session_stats = compute_statistics(boundary_results, segments)
    stats.to_csv(OUT / 'segmentation_statistics.csv', index=False)
    session_stats.to_csv(OUT / 'session_results.csv', index=False)

    build_examples(e, boundary_results).to_csv(OUT / 'boundary_examples.csv', index=False)

    weights = pd.DataFrame({'feature': feature_columns, 'coefficient': final_model[-1].coef_[0]})
    weights.sort_values('coefficient', key=np.abs, ascending=False).head(20).to_csv(OUT / 'scorer_feature_weights.csv', index=False)

    save_plots(calibration, segments)

    summary = {
        'threshold': threshold,
        'training_oof_f1': float(best.f1),
        'candidate_pool_size': int(len(candidates)),
        'candidate_recall': float(candidates.true_boundary.sum() / e.true_boundary.sum()),
        'heldout': {row.metric: row.value for _, row in stats[stats.scope == 'heldout'].iterrows()},
        'all_dataset_a': {row.metric: row.value for _, row in stats[stats.scope == 'all_dataset_a'].iterrows()},
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    main()
