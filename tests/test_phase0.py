import json
import pandas as pd
from src.event_parser import iter_events
from src.normalizer import normalize_event
from src.data_join import join_events_to_gt

def test_jsonl_reports_malformed(tmp_path):
    p=tmp_path/'events.jsonl'; p.write_text('{"event_id":"a"}\nnot-json\n',encoding='utf-8')
    rows=list(iter_events(p)); assert rows[0][1]['event_id']=='a'; assert rows[1][1] is None and 'error' in rows[1][2]

def test_normalization_and_join_half_open_boundary():
    raw={'event_id':'a','session_id':'s','timestamp_ms':1000,'timestamp_iso':'2026-01-01T00:00:01Z','layer':'L2','event_type':'keystroke','context':{'active_app':{'app_name':'App','process_name':'app.exe','window_title':'Title'},'active_browser_tab':None},'correlation':{'sequence_number':1},'payload':{'key':'A'},'extensions':{}}
    event=pd.DataFrame([normalize_event(raw,chunk_id='c',source_file='x',line_number=1)])
    gt=pd.DataFrame([{'session_id':'s','execution_id':'e','process_code':'P','process_name':'Process','domain':'d','variant':'v','start_ts':'2026-01-01T00:00:01Z','end_ts':'2026-01-01T00:00:02Z'}])
    assert join_events_to_gt(event,gt).iloc[0].execution_id=='e'
    event.loc[0,'timestamp_iso']='2026-01-01T00:00:02Z'
    assert join_events_to_gt(event,gt).iloc[0].gt_assignment=='unassigned'
