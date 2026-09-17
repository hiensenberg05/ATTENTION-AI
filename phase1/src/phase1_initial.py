import pandas as pd, numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'phase1/results/phase1_initial'; E=pd.read_parquet(ROOT/'outputs/tables/dataset_a_events_with_gt.parquet'); G=pd.read_parquet(ROOT/'outputs/tables/dataset_a_gt_executions.parquet')
E=E.sort_values(['session_id','timestamp_ms','raw_line_number']).copy(); E['prev_ts']=E.groupby('session_id').timestamp_ms.shift(); E['gap_seconds']=(E.timestamp_ms-E.prev_ts)/1000; E['prev_execution']=E.groupby('session_id').execution_id.shift(); E['prev_app']=E.groupby('session_id').active_app.shift(); E['prev_window']=E.groupby('session_id').window_title.shift(); E['true_boundary']=E.execution_id.notna()&E.prev_execution.notna()&(E.execution_id!=E.prev_execution); E['app_change']=E.active_app.ne(E.prev_app)&E.active_app.notna()&E.prev_app.notna(); E['window_change']=E.window_title.ne(E.prev_window)&E.window_title.notna()&E.prev_window.notna(); P=E[E.prev_ts.notna()].copy()
rows=[]
for t in [5,10,20,30,60]:
 for name,pred in [('gap',P.gap_seconds>t),('gap_or_app_change',(P.gap_seconds>t)|P.app_change)]:
  tp=int((pred&P.true_boundary).sum()); fp=int((pred&~P.true_boundary).sum()); fn=int((~pred&P.true_boundary).sum()); rows.append({'baseline':name,'threshold_seconds':t,'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else 0,'recall':tp/(tp+fn) if tp+fn else 0,'candidates':int(pred.sum())})
pd.DataFrame(rows).to_csv(OUT/'baseline_results.csv',index=False)
stats=[]
for label,x in [('true_boundary',P[P.true_boundary]),('within_execution',P[~P.true_boundary])]:
 stats += [{'group':label,'metric':'pairs','value':len(x)},{'group':label,'metric':'gap_median_seconds','value':x.gap_seconds.median()},{'group':label,'metric':'gap_p95_seconds','value':x.gap_seconds.quantile(.95)},{'group':label,'metric':'app_change_rate','value':x.app_change.mean()},{'group':label,'metric':'window_change_rate','value':x.window_change.mean()}]
pd.DataFrame(stats).to_csv(OUT/'boundary_statistics.csv',index=False)
signals=[]
for col in ['event_type','active_app','layer']:
 for group,x in [('boundary',P[P.true_boundary]),('within',P[~P.true_boundary])]:
  for value,n in x[col].fillna('<missing>').value_counts().head(15).items(): signals.append({'signal':col,'group':group,'value':value,'count':n,'rate':n/len(x)})
for col in ['app_change','window_change']:
 for group,x in [('boundary',P[P.true_boundary]),('within',P[~P.true_boundary])]: signals.append({'signal':col,'group':group,'value':'true','count':int(x[col].sum()),'rate':x[col].mean()})
pd.DataFrame(signals).to_csv(OUT/'signal_summary.csv',index=False)
examples=P[P.true_boundary][['session_id','timestamp_iso','gap_seconds','prev_execution','execution_id','prev_app','active_app','prev_window','window_title','event_type','app_change','window_change']].head(100); examples.to_csv(OUT/'boundary_examples.csv',index=False)
valid=G.dropna(subset=['start_ts','end_ts']).copy(); valid['duration_seconds']=(pd.to_datetime(valid.end_ts,utc=True)-pd.to_datetime(valid.start_ts,utc=True)).dt.total_seconds()
summary={'pairs':len(P),'true_boundary_pairs':int(P.true_boundary.sum()),'within_pairs':int((~P.true_boundary).sum()),'boundary_gap_median':float(P[P.true_boundary].gap_seconds.median()),'within_gap_median':float(P[~P.true_boundary].gap_seconds.median()),'boundary_app_change':float(P[P.true_boundary].app_change.mean()),'within_app_change':float(P[~P.true_boundary].app_change.mean()),'valid_execution_duration_median':float(valid.duration_seconds.median()),'continued_executions':int((valid.continues_from_prev.fillna(False)|valid.continues_to_next.fillna(False)).sum()),'split_executions':int(valid.split_id.notna().sum())}
(OUT/'metrics.txt').write_text('\n'.join(f'{k}={v}' for k,v in summary.items()))
