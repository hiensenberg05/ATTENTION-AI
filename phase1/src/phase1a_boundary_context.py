import pandas as pd, numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; O=ROOT/'phase1/results/phase1a_boundary_context'; E=pd.read_parquet(ROOT/'outputs/tables/dataset_a_events_with_gt.parquet').sort_values(['session_id','timestamp_ms','raw_line_number']).reset_index(drop=True)
E['prev_exec']=E.groupby('session_id').execution_id.shift(); E['boundary']=E.execution_id.notna()&E.prev_exec.notna()&(E.execution_id!=E.prev_exec); E['within']=E.execution_id.notna()&E.execution_id.eq(E.prev_exec)
# deterministic sampled within transitions, matched only by availability
B=E.index[E.boundary].to_numpy(); W=E.index[E.within].to_numpy(); rng=np.random.default_rng(42); W=rng.choice(W,size=min(len(W),len(B)),replace=False)
def feats(i,k):
 a=E.iloc[max(0,i-k):i]; z=E.iloc[i:min(len(E),i+k)];
 def x(d): return {'events':len(d),'gap_med':d.timestamp_ms.diff().median()/1000 if len(d)>1 else np.nan,'apps':d.active_app.nunique(),'windows':d.window_title.nunique(),'browser':d.event_type.str.startswith('browser_').mean(),'clipboard':d.event_type.eq('clipboard_change').mean(),'keys':d.event_type.isin(['keystroke','shortcut']).mean(),'clicks':d.event_type.isin(['mouse_click','browser_click']).mean(),'top_event':d.event_type.mode().iloc[0] if len(d) else None,'top_app':d.active_app.mode().iloc[0] if d.active_app.notna().any() else None}
 p=x(a); q=x(z); return {**{f'pre_{n}':v for n,v in p.items()},**{f'post_{n}':v for n,v in q.items()},'app_set_jaccard':len(set(a.active_app.dropna())&set(z.active_app.dropna()))/len(set(a.active_app.dropna())|set(z.active_app.dropna())) if len(set(a.active_app.dropna())|set(z.active_app.dropna())) else np.nan}
rows=[]
for label,inds in [('boundary',B),('within',W)]:
 for k in [10,20,50]:
  for i in inds:
   r=feats(i,k);r.update({'group':label,'window_events':k,'session_id':E.at[i,'session_id'],'timestamp_iso':E.at[i,'timestamp_iso'],'execution_id':E.at[i,'execution_id'],'previous_execution_id':E.at[i,'prev_exec']});rows.append(r)
D=pd.DataFrame(rows); D.to_csv(O/'boundary_context_examples.csv',index=False)
num=D.select_dtypes('number').columns; stats=D.groupby(['group','window_events'])[[c for c in num if c!='window_events']].mean().reset_index();stats.to_csv(O/'context_statistics.csv',index=False)
comp=[]
for k in [10,20,50]:
 for col in [c for c in num if c not in ['window_events']]:
  b=D[(D.group=='boundary')&(D.window_events==k)][col].mean(); w=D[(D.group=='within')&(D.window_events==k)][col].mean();comp.append({'window_events':k,'signal':col,'boundary_mean':b,'within_mean':w,'difference':b-w})
pd.DataFrame(comp).to_csv(O/'signal_comparison.csv',index=False)
