"""Half-open temporal assignment for Dataset A exploration."""
import pandas as pd

def join_events_to_gt(events, executions):
    out=events.copy(); out['execution_id']=None; out['gt_process_code']=None; out['gt_process_name']=None; out['gt_domain']=None; out['gt_variant']=None; out['gt_assignment']='unassigned'; out['_event_ts']=pd.to_datetime(out.timestamp_iso,utc=True,errors='coerce')
    valid=executions.dropna(subset=['start_ts','end_ts']).copy(); valid['_start']=pd.to_datetime(valid.start_ts,utc=True); valid['_end']=pd.to_datetime(valid.end_ts,utc=True)
    for sid,g in valid.groupby('session_id'):
        session_index=out.index[out.session_id.eq(sid)]
        for _,e in g.iterrows():
            ix=session_index[(out.loc[session_index,'_event_ts']>=e._start)&(out.loc[session_index,'_event_ts']<e._end)]
            out.loc[ix,['execution_id','gt_process_code','gt_process_name','gt_domain','gt_variant','gt_assignment']]=[e.execution_id,e.process_code,e.process_name,e.domain,e.variant,'assigned']
    return out.drop(columns='_event_ts')
