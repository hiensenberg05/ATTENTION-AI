"""Non-destructive GT validation."""
import pandas as pd

def validate_gt(executions, raw_gt):
    findings=[]
    for _,r in executions[executions.end_ts.isna()].iterrows(): findings.append({'session_id':r.session_id,'severity':'warning','check':'missing_end_ts','execution_id':r.execution_id,'detail':'Manifest execution has no end_ts'})
    valid=executions.dropna(subset=['start_ts','end_ts']).copy(); valid['start']=pd.to_datetime(valid.start_ts,utc=True); valid['end']=pd.to_datetime(valid.end_ts,utc=True)
    for _,r in valid[valid.end<=valid.start].iterrows(): findings.append({'session_id':r.session_id,'severity':'error','check':'invalid_duration','execution_id':r.execution_id,'detail':'end_ts is not after start_ts'})
    for sid,g in valid.sort_values('start').groupby('session_id'):
        previous=None
        for _,r in g.iterrows():
            if previous is not None and r.start<previous.end: findings.append({'session_id':sid,'severity':'warning','check':'overlapping_execution','execution_id':r.execution_id,'detail':f'Overlaps {previous.execution_id}'})
            previous=r
    starts=raw_gt[raw_gt.event.eq('process_started')].copy(); starts['previous_code']=starts.groupby('session_id').process_code.shift()
    for _,r in starts[starts.process_code.eq(starts.previous_code)].iterrows(): findings.append({'session_id':r.session_id,'severity':'warning','check':'duplicate_process_start','execution_id':None,'detail':str(r.process_code)})
    continued=executions[executions.continues_from_prev.fillna(False)|executions.continues_to_next.fillna(False)]
    for _,r in continued.iterrows(): findings.append({'session_id':r.session_id,'severity':'info','check':'cross_chunk_or_continuation','execution_id':r.execution_id,'detail':'Continuation flag set'})
    return pd.DataFrame(findings,columns=['session_id','severity','check','execution_id','detail'])
