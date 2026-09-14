"""One row per valid GT execution; exploratory features, no model."""
import pandas as pd

def build_process_features(events,executions):
    valid=executions.dropna(subset=['start_ts','end_ts']).copy(); valid['duration_seconds']=(pd.to_datetime(valid.end_ts,utc=True)-pd.to_datetime(valid.start_ts,utc=True)).dt.total_seconds(); rows=[]
    for _,e in valid.iterrows():
        x=events[events.execution_id.eq(e.execution_id)].sort_values(['timestamp_ms','raw_line_number']); row=e.to_dict(); row.update({'total_events':len(x),'unique_apps':x.active_app.nunique(),'unique_windows':x.window_title.nunique(),'unique_browser_urls':x.browser_url.nunique(),'first_app':x.active_app.iloc[0] if len(x) else None,'last_app':x.active_app.iloc[-1] if len(x) else None,'dominant_app':x.active_app.mode().iloc[0] if x.active_app.notna().any() else None,'application_transition_sequence':' > '.join(x.active_app.dropna().drop_duplicates().tolist()),'click_count':x.event_type.eq('mouse_click').sum(),'keystroke_count':x.event_type.eq('keystroke').sum(),'browser_event_count':x.event_type.str.startswith('browser_').sum(),'clipboard_count':x.event_type.eq('clipboard_change').sum(),'scroll_count':x.event_type.eq('mouse_scroll').sum(),'app_switch_count':x.event_type.eq('app_switch').sum()}); rows.append(row)
    return pd.DataFrame(rows)
