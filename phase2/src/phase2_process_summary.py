"""Phase 2C (aggregation)/2D/2E/2F/2G: builds process_summary.csv, variant_analysis.csv,
automation_candidates.csv, representative_segments.csv, segments.jsonl (final labels), and plots,
from segment_features.csv produced by phase2_process_analysis.py. Pure aggregation/analysis over
already-computed, already-grouped segments -- no boundary detection, no retraining, no Dataset A
GT involved.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Phase 2 builds directly on the frozen Phase 1F scorer, so Phase 1's modules
# must be importable. They live in a sibling folder, not on the default path.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'phase1' / 'src'))

import phase2_dataset_b_segmentation as p2a

ROOT = p2a.ROOT
OUT = p2a.OUT
PLOTS = OUT / 'plots'
PLOTS.mkdir(exist_ok=True, parents=True)

MIN_EXECUTIONS = 3  # matches phase2_process_analysis.MIN_EXECUTIONS_FOR_PROCESS_TYPE

ROUTE_DESCRIPTIONS = {
    'payroll-items': 'payroll line-item review/entry',
    'leave-applications': 'leave application handling',
    'onboarding': 'employee onboarding workflow',
    'resident-tax': 'resident tax notice handling',
    'social-insurance': 'social insurance processing',
    'dashboard': 'system dashboard / landing page browsing',
}


def auto_description(primary_context, dominant_app):
    if '#' in primary_context:
        host, route = primary_context.split('#', 1)
        desc = ROUTE_DESCRIPTIONS.get(route, route.replace('-', ' '))
        return f'{desc} (web app at {host})'
    if primary_context == dominant_app:
        return f'{dominant_app} desktop activity (no browser route captured)'
    return primary_context


def confidence_level(row):
    if row['is_rare_or_catchall']:
        return 'Low'
    has_route = '#' in row['primary_context']
    strong_content = row['case_id_presence_fraction'] > 0.15 or row['extracted_text_presence_fraction'] > 0.3
    if has_route and (row['n_executions'] >= 8) and strong_content:
        return 'High'
    if has_route and row['n_executions'] >= MIN_EXECUTIONS:
        return 'Medium'
    return 'Low'


def slug(ctx):
    return 'B-' + ctx.replace(' ', '_').replace('/', '_').replace(':', '_').replace('#', '_')[:40]


def build_process_summary(audit):
    """Grouped by primary_context (the process FAMILY, e.g. '5132 payroll-items' across all its
    v1/v2/... sub-variants) -- not by the finer process_type_id_collapsed sub-variant split, which
    would make every process type look like it has exactly one variant. Sub-variant detail lives
    in variant_analysis.csv."""
    total_segments = len(audit)
    rows = []
    for primary_context, g in audit.groupby('primary_context'):
        ptid = slug(primary_context)
        dominant_app = g.dominant_application.mode().iloc[0] if g.dominant_application.notna().any() else None
        variants = sorted(g.process_type_id.unique().tolist())
        is_rare_or_catchall = len(g) < MIN_EXECUTIONS
        by_duration = g.sort_values('duration_seconds')
        representative_ids = sorted(set([
            by_duration.segment_id.iloc[len(by_duration) // 2],
            by_duration.segment_id.iloc[0],
            by_duration.segment_id.iloc[-1],
        ]))
        sample_case_ids = sorted(set(';'.join(g.available_case_ids.dropna()).split(';')) - {''})
        row = {
            'process_type_id': ptid,
            'primary_context': primary_context,
            'human_readable_description': auto_description(primary_context, dominant_app),
            'n_executions': len(g),
            'pct_of_dataset_b_executions': round(100 * len(g) / total_segments, 2),
            'n_sessions': g.session_id.nunique(),
            'n_workers': g.worker_machine_id.nunique(),
            'workers': ';'.join(sorted(g.worker_machine_id.unique())),
            'median_duration_seconds': round(g.duration_seconds.median(), 2),
            'p25_duration_seconds': round(g.duration_seconds.quantile(0.25), 2),
            'p75_duration_seconds': round(g.duration_seconds.quantile(0.75), 2),
            'total_observed_minutes': round(g.duration_seconds.sum() / 60, 2),
            'median_event_count': g.event_count.median(),
            'median_clicks': (g.click_count + g.browser_click_count).median(),
            'median_keystrokes': g.keystroke_count.median(),
            'median_total_interactions': g.total_interaction_events.median(),
            'dominant_application': dominant_app,
            'browser_involvement_fraction': round((g.browser_activity_count > 0).mean(), 3),
            'n_meaningful_variants': len(variants),
            'variant_ids': ';'.join(variants),
            'representative_segment_ids': ';'.join(representative_ids),
            'case_id_presence_fraction': round((g.case_id_count > 0).mean(), 3),
            'sample_case_ids': ';'.join(sample_case_ids[:5]),
            'extracted_text_presence_fraction': round(g.has_extracted_text.mean(), 3),
            'screenshot_presence_fraction': round(g.has_screenshot.mean(), 3),
            'crosses_chunk_fraction': round(g.crosses_chunk.mean(), 3),
            'duration_cv': round(g.duration_seconds.std() / g.duration_seconds.mean(), 3) if g.duration_seconds.mean() else None,
            'is_rare_or_catchall': is_rare_or_catchall,
        }
        row['confidence_level'] = confidence_level(row)
        row['evidence_supporting_interpretation'] = (
            f"{len(g)} segments across {g.session_id.nunique()} sessions/{g.worker_machine_id.nunique()} workers; "
            f"dominant app {dominant_app}; browser involvement {row['browser_involvement_fraction']:.0%}; "
            f"case-ID evidence in {row['case_id_presence_fraction']:.0%} of executions"
            + (f" (samples: {', '.join(sample_case_ids[:3])})" if sample_case_ids else "")
            + f"; extracted screen text present in {row['extracted_text_presence_fraction']:.0%}."
        )
        rows.append(row)
    return pd.DataFrame(rows).sort_values('n_executions', ascending=False)


def build_variant_analysis(audit):
    rows = []
    for ctx, g in audit.groupby('primary_context'):
        variants = sorted(g.process_type_id.unique())
        if len(variants) < 2:
            continue
        overall_median_dur = g.duration_seconds.median()
        overall_median_events = g.event_count.median()
        for vid in variants:
            vg = g[g.process_type_id == vid]
            dur_ratio = (vg.duration_seconds.median() / overall_median_dur) if overall_median_dur else np.nan
            event_ratio = (vg.event_count.median() / overall_median_events) if overall_median_events else np.nan
            # simple, documented rule: a variant whose median duration/event count differs from
            # the context's overall median by less than 40% is treated as a minor/optional branch
            # of the same workflow; larger differences are flagged for manual review as possibly
            # a genuinely different process sharing the same application/route.
            close_enough = 0.6 <= dur_ratio <= 1.67 and 0.6 <= event_ratio <= 1.67
            rows.append({
                'primary_context': ctx, 'variant_id': vid,
                'frequency': len(vg), 'pct_of_context': round(100 * len(vg) / len(g), 1),
                'median_duration_seconds': round(vg.duration_seconds.median(), 2),
                'duration_ratio_vs_context_median': round(dur_ratio, 2) if pd.notna(dur_ratio) else None,
                'median_event_count': vg.event_count.median(),
                'event_count_ratio_vs_context_median': round(event_ratio, 2) if pd.notna(event_ratio) else None,
                'interpretation': 'likely optional branch of same workflow' if close_enough else 'possibly a different process sharing the same app/route -- needs manual review',
                'same_automation_plausible': bool(close_enough),
                'n_workers': vg.worker_machine_id.nunique(),
                'representative_segment_id': vg.sort_values('duration_seconds').segment_id.iloc[len(vg) // 2],
            })
    return pd.DataFrame(rows).sort_values(['primary_context', 'frequency'], ascending=[True, False])


def tier(value, low, high):
    if value >= high:
        return 'High'
    if value >= low:
        return 'Medium'
    return 'Low'


def build_automation_candidates(summary):
    cand = summary[~summary.is_rare_or_catchall].copy()
    if cand.empty:
        return cand
    max_minutes = cand.total_observed_minutes.max()
    cand['impact_tier'] = cand.total_observed_minutes.apply(lambda v: tier(v / max_minutes, 0.15, 0.4))
    cand['repeatability_tier'] = cand.apply(
        lambda r: tier(1.0 if (r.duration_cv or 1) < 0.5 else (0.5 if r.n_executions >= 8 else 0.2), 0.4, 0.8), axis=1)
    cand['feasibility_tier'] = cand.apply(
        lambda r: tier((r.browser_involvement_fraction >= 0.8) * 0.6 + (r.n_meaningful_variants <= 2) * 0.4, 0.4, 0.8), axis=1)
    cand['evidence_quality_tier'] = cand.apply(
        lambda r: tier(0.5 * r.case_id_presence_fraction + 0.5 * r.extracted_text_presence_fraction, 0.15, 0.35), axis=1)
    cand['complexity_risk_tier'] = cand.apply(
        lambda r: tier((r.n_meaningful_variants >= 3) * 0.4 + (r.crosses_chunk_fraction > 0.1) * 0.3 + (r.n_workers <= 1) * 0.3, 0.4, 0.7), axis=1)

    cols = ['process_type_id', 'human_readable_description', 'n_executions', 'pct_of_dataset_b_executions',
            'total_observed_minutes', 'median_duration_seconds', 'duration_cv', 'n_workers', 'n_sessions',
            'n_meaningful_variants', 'median_clicks', 'median_keystrokes', 'median_total_interactions',
            'dominant_application', 'browser_involvement_fraction', 'case_id_presence_fraction',
            'extracted_text_presence_fraction', 'confidence_level',
            'impact_tier', 'repeatability_tier', 'feasibility_tier', 'evidence_quality_tier', 'complexity_risk_tier',
            'evidence_supporting_interpretation']
    return cand[cols].sort_values('total_observed_minutes', ascending=False)


def build_representative_segments(audit, summary):
    rows = []
    for _, prow in summary.iterrows():
        ids = prow.representative_segment_ids.split(';')
        for sid in ids:
            seg = audit[audit.segment_id == sid]
            if seg.empty:
                continue
            s = seg.iloc[0]
            rows.append({
                'process_type_id': prow.process_type_id, 'segment_id': s.segment_id, 'session_id': s.session_id,
                'start_timestamp': s.start_timestamp, 'end_timestamp': s.end_timestamp,
                'duration_seconds': s.duration_seconds, 'event_count': s.event_count,
                'dominant_application': s.dominant_application, 'applications_used': s.applications_used,
                'browser_routes': s.browser_routes, 'available_case_ids': s.available_case_ids,
                'click_count': s.click_count, 'keystroke_count': s.keystroke_count,
                'form_input_count': s.form_input_count, 'navigation_count': s.navigation_count,
                'has_extracted_text': s.has_extracted_text, 'has_screenshot': s.has_screenshot,
            })
    return pd.DataFrame(rows)


def write_segments_jsonl(audit):
    """Label = the process-FAMILY id (primary_context slug), so sub-variants of the same
    recurring work unit get the same label by default, per variant_analysis.csv's
    'likely optional branch' finding for the large majority of variants (see phase2_summary.md).
    This is a deterministic identifier derived mechanically from dominant app/browser route, not
    an invented business name.

    Written to two paths from one string: `phase2/results/` (where it belongs as a
    phase output) and `deliverables/` (where it is submitted from). Copying it
    afterwards would let the submitted file drift silently behind a rerun; writing
    both here makes that impossible."""
    lines = []
    for r in audit.sort_values(['session_id', 'start_timestamp']).itertuples():
        lines.append(json.dumps({
            'session_id': r.session_id, 'start': r.start_timestamp, 'end': r.end_timestamp,
            'label': slug(r.primary_context),
        }, ensure_ascii=False))
    payload = '\n'.join(lines) + '\n'

    deliverables = ROOT / 'deliverables'
    deliverables.mkdir(exist_ok=True)
    for target in (OUT / 'segments.jsonl', deliverables / 'segments.jsonl'):
        target.write_text(payload, encoding='utf-8')


def make_plots(audit, summary):
    top = summary[~summary.is_rare_or_catchall].sort_values('n_executions', ascending=False).head(15)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top.human_readable_description[::-1], top.n_executions[::-1])
    ax.set_xlabel('executions'); ax.set_title('Dataset B: process frequency (top 15)')
    fig.tight_layout(); fig.savefig(PLOTS / 'process_frequency.png', dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    top2 = summary[~summary.is_rare_or_catchall].sort_values('total_observed_minutes', ascending=False).head(15)
    ax.barh(top2.human_readable_description[::-1], top2.total_observed_minutes[::-1])
    ax.set_xlabel('total observed minutes'); ax.set_title('Dataset B: total observed time by process (top 15)')
    fig.tight_layout(); fig.savefig(PLOTS / 'total_time_by_process.png', dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(audit.duration_seconds.clip(upper=audit.duration_seconds.quantile(0.99)), bins=40)
    ax.set_xlabel('segment duration (seconds, 99th pct clipped)'); ax.set_ylabel('count')
    ax.set_title('Dataset B: segment duration distribution')
    fig.tight_layout(); fig.savefig(PLOTS / 'duration_distribution.png', dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(audit.total_interaction_events.clip(upper=audit.total_interaction_events.quantile(0.99)), bins=40)
    ax.set_xlabel('interaction events per segment (99th pct clipped)'); ax.set_ylabel('count')
    ax.set_title('Dataset B: interaction burden distribution')
    fig.tight_layout(); fig.savefig(PLOTS / 'interaction_burden.png', dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    vc = audit.process_type_id_collapsed.value_counts()
    ax.bar(range(len(vc)), vc.values)
    ax.set_xticks([]); ax.set_ylabel('executions'); ax.set_xlabel(f'{len(vc)} process/variant groups, sorted by frequency')
    ax.set_title('Dataset B: process/variant distribution (all groups)')
    fig.tight_layout(); fig.savefig(PLOTS / 'process_variant_distribution.png', dpi=160); plt.close(fig)


def main():
    audit = pd.read_csv(OUT / 'segment_features.csv')
    summary = build_process_summary(audit)
    summary.to_csv(OUT / 'process_summary.csv', index=False)

    variants = build_variant_analysis(audit)
    variants.to_csv(OUT / 'variant_analysis.csv', index=False)

    candidates = build_automation_candidates(summary)
    candidates.to_csv(OUT / 'automation_candidates.csv', index=False)

    representative = build_representative_segments(audit, summary)
    representative.to_csv(OUT / 'representative_segments.csv', index=False)

    write_segments_jsonl(audit)
    make_plots(audit, summary)

    print(f'process types (raw): {audit.process_type_id.nunique()}, collapsed: {audit.process_type_id_collapsed.nunique()}')
    print(f'automation candidates (>= {MIN_EXECUTIONS} executions, non-catchall): {len(candidates)}')
    print(candidates[['process_type_id', 'n_executions', 'total_observed_minutes', 'confidence_level']].to_string(index=False))


if __name__ == '__main__':
    main()
