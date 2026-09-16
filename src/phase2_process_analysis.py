"""Phase 2B-2G: characterize Dataset B's recovered segments, group them into recurring process
types via a transparent rule-based method (no ML clustering, no embeddings, no LLM), analyze
variants, and compute the quantitative side of the automation-opportunity analysis.

Reads only what Phase 2A produced (`phase2_dataset_b/raw_segments.csv`, the frozen candidate/event
data it was built from) plus Dataset B's own event table. Does not touch Phase 1, does not read
Dataset A ground truth, does not retrain or reselect anything.

GROUPING METHOD (documented in full here since it's the one genuinely new piece of logic in this
phase): each segment gets a `primary_context` -- its dominant non-browser application, or, for
browser-dominant segments, the browser's host:port plus the first hash-route segment (e.g.
`127.0.0.1:5133#payroll-items`), since Dataset B's line-of-business systems are distinguished by
that route, not by the browser window title. Within each `primary_context`, segments are further
split by cosine similarity of their event-type-rate vectors using deterministic single-linkage
grouping (union-find, similarity threshold documented as SIMILARITY_THRESHOLD below) -- no
randomness, no iterative optimization, fully reproducible from the same input every time.
"""
from pathlib import Path
from urllib.parse import urlparse
import json

import numpy as np
import pandas as pd

import phase1f4_segmentation as p1f4
import phase2_dataset_b_segmentation as p2a

ROOT = p2a.ROOT
OUT = p2a.OUT
PLOTS = OUT / 'plots'
PLOTS.mkdir(exist_ok=True, parents=True)

SIMILARITY_THRESHOLD = 0.80
MIN_EXECUTIONS_FOR_PROCESS_TYPE = 3

CLICK_TYPES = ['mouse_click', 'mouse_double_click']
KEYSTROKE_TYPES = ['keystroke']


def machine_from_session(session_id):
    return session_id.rsplit('-', 1)[-1]


def build_segment_audit(e, segments):
    rows = []
    for seg in segments.itertuples():
        x = e.loc[seg.start_row:seg.end_row]
        app_counts = x.active_app.value_counts()
        dominant_app = app_counts.index[0] if len(app_counts) else None
        apps_used = sorted(x.active_app.dropna().unique().tolist())
        event_type_counts = x.event_type.value_counts().to_dict()
        browser_mask = x.event_type.str.startswith('browser_')
        urls = sorted(x.browser_url.dropna().unique().tolist())
        domains = sorted({urlparse(u).netloc for u in urls if u})
        routes = sorted({(urlparse(u).netloc + '#' + urlparse(u).fragment.split('/')[1]) if '/' in urlparse(u).fragment else urlparse(u).netloc for u in urls if u})
        text_source = x.extracted_text.combine_first(x.clipboard_text).dropna()
        case_ids = sorted(set().union(*[p1f4.extract_case_ids(t) for t in text_source])) if len(text_source) else []
        rows.append({
            'segment_id': seg.segment_id, 'session_id': seg.session_id,
            'worker_machine_id': machine_from_session(seg.session_id),
            'start_timestamp': seg.start_timestamp, 'end_timestamp': seg.end_timestamp,
            'duration_seconds': round(seg.duration_seconds, 3), 'event_count': seg.event_count,
            'start_event_id': seg.start_event_id, 'end_event_id': seg.end_event_id,
            'start_chunk_id': seg.start_chunk_id, 'end_chunk_id': seg.end_chunk_id,
            'crosses_chunk': seg.crosses_chunk,
            'dominant_application': dominant_app,
            'applications_used': ';'.join(apps_used),
            'num_applications': len(apps_used),
            'browser_activity_count': int(browser_mask.sum()),
            'browser_domains': ';'.join(domains),
            'browser_routes': ';'.join(routes),
            'browser_url_count': len(urls),
            'event_type_counts_json': json.dumps(event_type_counts, ensure_ascii=False),
            'click_count': int(x.event_type.isin(CLICK_TYPES).sum()),
            'browser_click_count': int(x.event_type.eq('browser_click').sum()),
            'keystroke_count': int(x.event_type.isin(KEYSTROKE_TYPES).sum()),
            'shortcut_count': int(x.event_type.eq('shortcut').sum()),
            'form_input_count': int(x.event_type.eq('browser_form_input').sum()),
            'navigation_count': int(x.event_type.eq('browser_navigation').sum()),
            'app_switch_count': int(x.event_type.eq('app_switch').sum()),
            'scroll_count': int(x.event_type.eq('mouse_scroll').sum()),
            'clipboard_change_count': int(x.event_type.eq('clipboard_change').sum()),
            'total_interaction_events': int(x.event_type.isin(
                CLICK_TYPES + KEYSTROKE_TYPES + ['shortcut', 'browser_click', 'browser_form_input', 'browser_navigation', 'mouse_scroll', 'mouse_drag_drop']
            ).sum()),
            'available_case_ids': ';'.join(case_ids),
            'case_id_count': len(case_ids),
            'extracted_text_event_count': int(x.extracted_text.notna().sum()),
            'has_extracted_text': bool(x.extracted_text.notna().any()),
            'screenshot_event_count': int(x.screenshot_filename.notna().sum()),
            'has_screenshot': bool(x.screenshot_filename.notna().any()),
        })
    return pd.DataFrame(rows)


def primary_context(row):
    if row.dominant_application != 'Microsoft Edge' or not row.browser_routes:
        return row.dominant_application or 'unknown'
    return sorted(row.browser_routes.split(';'))[0]


EVENT_TYPE_VOCAB = [
    'app_switch', 'keystroke', 'shortcut', 'mouse_click', 'mouse_double_click', 'mouse_scroll',
    'mouse_drag_drop', 'clipboard_change', 'text_input_complete', 'window_title_change',
    'window_state_change', 'dialog_opened', 'dialog_closed', 'screenshot_smart', 'browser_click',
    'browser_form_input', 'browser_navigation', 'browser_tab_event', 'browser_alert', 'browser_error',
]


def event_rate_vector(counts_json, total):
    counts = json.loads(counts_json)
    return np.array([counts.get(v, 0) / total if total else 0.0 for v in EVENT_TYPE_VOCAB])


def cosine_sim(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, i, j):
        ri, rj = self.find(i), self.find(j)
        if ri != rj:
            self.parent[ri] = rj


def group_process_types(audit):
    audit = audit.copy()
    audit['primary_context'] = audit.apply(primary_context, axis=1)
    audit['event_rate_vec'] = audit.apply(lambda r: event_rate_vector(r.event_type_counts_json, r.event_count), axis=1)

    process_type_id = pd.Series(index=audit.index, dtype=object)
    for ctx, idx in audit.groupby('primary_context').groups.items():
        idx = list(idx)
        vecs = [audit.loc[i, 'event_rate_vec'] for i in idx]
        uf = UnionFind(len(idx))
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                if cosine_sim(vecs[a], vecs[b]) >= SIMILARITY_THRESHOLD:
                    uf.union(a, b)
        roots = [uf.find(a) for a in range(len(idx))]
        unique_roots = sorted(set(roots))
        root_to_sub = {r: i + 1 for i, r in enumerate(unique_roots)}
        ctx_slug = ctx.replace(' ', '_').replace('/', '_').replace(':', '_').replace('#', '_')[:40]
        for a, i in enumerate(idx):
            sub = root_to_sub[roots[a]]
            n_subs = len(unique_roots)
            process_type_id[i] = f'B-{ctx_slug}' if n_subs == 1 else f'B-{ctx_slug}-v{sub}'

    audit['process_type_id'] = process_type_id
    return audit.drop(columns=['event_rate_vec'])


def collapse_small_groups(audit):
    """Process types with fewer than MIN_EXECUTIONS_FOR_PROCESS_TYPE executions are relabeled
    into a shared 'other/rare' bucket per primary_context so process_summary.csv reports stable
    recurring types separately from one-off/rare activity -- documented, not discarded (every
    segment keeps its original process_type_id in process_groups.csv for full traceability)."""
    counts = audit.process_type_id.value_counts()
    small = set(counts[counts < MIN_EXECUTIONS_FOR_PROCESS_TYPE].index)

    def slug(ctx):
        return 'B-' + ctx.replace(' ', '_').replace('/', '_').replace(':', '_').replace('#', '_')[:40]

    audit['process_type_id_collapsed'] = audit.apply(
        lambda r: f'{slug(r.primary_context)}-other' if r.process_type_id in small else r.process_type_id, axis=1,
    )
    return audit


def main():
    e, candidates, segments = None, None, None
    e = p2a.load_events_b()
    segments = pd.read_csv(OUT / 'raw_segments.csv')

    audit = build_segment_audit(e, segments)
    audit = group_process_types(audit)
    audit = collapse_small_groups(audit)
    audit.to_csv(OUT / 'segment_features.csv', index=False)

    process_groups = audit[['segment_id', 'session_id', 'worker_machine_id', 'primary_context',
                             'process_type_id', 'process_type_id_collapsed', 'duration_seconds',
                             'event_count', 'dominant_application']].copy()
    process_groups.to_csv(OUT / 'process_groups.csv', index=False)

    print(f'{len(audit)} segments grouped into {audit.process_type_id.nunique()} raw process types, '
          f'{audit.process_type_id_collapsed.nunique()} after collapsing types with < {MIN_EXECUTIONS_FOR_PROCESS_TYPE} executions')
    print(audit.process_type_id_collapsed.value_counts().to_string())
    return audit


if __name__ == '__main__':
    main()
