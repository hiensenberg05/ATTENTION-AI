import pandas as pd, numpy as np
from pathlib import Path
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support
R=Path(__file__).resolve().parents[2];O=R/'phase1/results/phase1b_segmentation';e=pd.read_parquet(R/'outputs/tables/dataset_a_events_with_gt.parquet').sort_values(['session_id','timestamp_ms','raw_line_number']).reset_index(drop=True)
e['p']=e.groupby('session_id').execution_id.shift();e['pt']=e.groupby('session_id').timestamp_ms.shift();e['y']=(e.execution_id.notna()&e.p.notna()&e.execution_id.ne(e.p)).astype(int);e['gap']=((e.timestamp_ms-e.pt)/1000).clip(0,120);e['app']=(e.active_app.ne(e.groupby('session_id').active_app.shift())).astype(int);e['win']=(e.window_title.ne(e.groupby('session_id').window_title.shift())).astype(int)
for k in [10,20]:
 for n,v in {'browser':e.event_type.str.startswith('browser_'),'keys':e.event_type.isin(['keystroke','shortcut']),'clipboard':e.event_type.eq('clipboard_change'),'clicks':e.event_type.isin(['mouse_click','browser_click'])}.items(): e[f'pre_{n}{k}']=v.groupby(e.session_id).transform(lambda x:x.shift().rolling(k,1).mean())
f=['gap','app','win']+[c for c in e if c.startswith('pre_')];d=e[e.execution_id.notna()&e.p.notna()].fillna(0); ss=sorted(d.session_id.unique());te=set(ss[::5]);tr=set(ss)-te;m=make_pipeline(StandardScaler(),LogisticRegression(class_weight='balanced',max_iter=500));m.fit(d[d.session_id.isin(tr)][f],d[d.session_id.isin(tr)].y);x=d[d.session_id.isin(te)].copy();x['score']=m.predict_proba(x[f])[:,1];x['pred']=x.score>=.5
rows=[]
for name,p in [('logistic',x.pred),('gap_5',x.gap>5),('gap_20',x.gap>20)]:
 a,b,c,_=precision_recall_fscore_support(x.y,p,average='binary',zero_division=0);rows.append({'method':name,'precision':a,'recall':b,'f1':c,'predicted_boundaries':int(p.sum()),'true_boundaries':int(x.y.sum())})
pd.DataFrame(rows).to_csv(O/'model_results.csv',index=False);pd.DataFrame({'feature':f,'coefficient':m[-1].coef_[0]}).to_csv(O/'feature_statistics.csv',index=False);x[['session_id','timestamp_iso','y','score','pred','gap','active_app','event_type','execution_id']].head(1000).to_csv(O/'segment_examples.csv',index=False);x[['session_id','timestamp_iso','y','score','pred','gap','active_app','event_type','execution_id']].assign(active_app=lambda q:q.active_app.astype('string'), event_type=lambda q:q.event_type.astype('string'), execution_id=lambda q:q.execution_id.astype('string')).to_parquet(O/'predictions'/'heldout_transition_predictions.parquet',index=False);print(pd.DataFrame(rows))

