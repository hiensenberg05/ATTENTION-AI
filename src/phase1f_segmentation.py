from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
R=Path(__file__).resolve().parents[1]; O=R/'phase1f_segmentation'; P=O/'plots'; O.mkdir(exist_ok=True);P.mkdir(exist_ok=True)
W=20; SEP=3

def change(a,b): return a.notna()&b.notna()&a.ne(b)
def metrics(y,p): return tuple(float(x) for x in precision_recall_fscore_support(y,p,average='binary',zero_division=0)[:3])
def select(d,t):
 out=[]
 for _,r in d.sort_values(['score','event_index'],ascending=[False,True]).iterrows():
  if r.score>=t and all(abs(int(r.event_index)-int(z.event_index))>=SEP for z in out): out.append(r)
 return {int(r.row_id) for r in out}
def context(s,idx,side):
 lo,hi=(max(s.index.min(),idx-8),idx-1) if side=='pre' else (idx,min(s.index.max(),idx+7));x=s.loc[lo:hi]; text=x.extracted_text.combine_first(x.clipboard_text).dropna()
 return (' > '.join(x.event_type.astype(str)),' > '.join(x.active_app.dropna().astype(str).drop_duplicates().tolist()[:4]),' > '.join(x.window_title.dropna().astype(str).drop_duplicates().str[:80].tolist()[:3]),str(text.iloc[-1 if side=='pre' else 0])[:200] if len(text) else '')
def features(s,inds,vocab):
 rows=[]; acts={'keyboard':{'keystroke','shortcut','text_input_complete'},'mouse':{'mouse_click','mouse_double_click','mouse_scroll','mouse_drag_drop'},'browser':{'browser_click','browser_form_input','browser_navigation','browser_tab_event','browser_alert','browser_error'},'clipboard':{'clipboard_change'}}
 for idx in inds:
  r=s.loc[idx]; pre=s.loc[max(s.index.min(),idx-W):idx-1];post=s.loc[idx:min(s.index.max(),idx+W)];q={'row_id':int(idx),'session_id':r.session_id,'timestamp_iso':r.timestamp_iso,'event_index':int(r.event_index),'gap_seconds':float(r.gap_seconds),'interaction_change':int(r.interaction_change),'app_change':int(r.app_change),'window_change':int(r.window_change),'browser_context_change':int(r.browser_context_change),'chunk_change':int(r.chunk_change)}
  for side,x in [('pre',pre),('post',post)]:
   n=max(len(x),1);q[side+'_gap_mean']=float(x.gap_seconds.mean()) if len(x) else 0;q[side+'_gap_max']=float(x.gap_seconds.max()) if len(x) else 0
   for nam,col in [('app_switch','app_change'),('window_switch','window_change'),('browser_context','browser_context_change')]: q[f'{side}_{nam}_rate']=float(x[col].mean()) if len(x) else 0
   for nam,col in [('apps','active_app'),('windows','window_title'),('tabs','browser_tab_id')]:q[f'{side}_unique_{nam}']=float(x[col].nunique())
   q[f'{side}_text_available_rate']=float((x.extracted_text.notna()|x.clipboard_text.notna()).mean()) if len(x) else 0
   for nam,types in acts.items():q[f'{side}_{nam}_rate']=float(x.event_type.isin(types).sum()/n)
   for v in vocab:q[f'{side}_event_{v}']=float((x.event_type==v).sum()/n)
  bases=['gap_mean','gap_max','app_switch_rate','window_switch_rate','browser_context_rate','unique_apps','unique_windows','unique_tabs','text_available_rate','keyboard_rate','mouse_rate','browser_rate','clipboard_rate']+[f'event_{v}' for v in vocab]
  for b in bases:q['delta_'+b]=q['post_'+b]-q['pre_'+b]
  rows.append(q)
 return pd.DataFrame(rows)

e=pd.read_parquet(R/'outputs/tables/dataset_a_events_with_gt.parquet').sort_values(['session_id','timestamp_ms','raw_line_number']).reset_index(drop=True);e['event_index']=e.groupby('session_id').cumcount();z=e.groupby('session_id').shift();e['previous_event_type']=z.event_type;e['previous_execution']=z.execution_id;e['gap_seconds']=((e.timestamp_ms-z.timestamp_ms)/1000).clip(0,120).fillna(0);e['interaction_change']=e.previous_event_type.notna()&e.event_type.ne(e.previous_event_type);e['app_change']=change(e.active_app,z.active_app);e['window_change']=change(e.window_title,z.window_title);e['browser_context_change']=change(e.browser_url,z.browser_url)|change(e.browser_tab_id,z.browser_tab_id);e['chunk_change']=e.chunk_id.ne(z.chunk_id)&z.chunk_id.notna();e['true_boundary']=(e.execution_id.notna()&e.previous_execution.notna()&e.execution_id.ne(e.previous_execution)).astype(int)
# High-recall pool: interaction transition plus operational signals. Chunks are never candidates alone.
e['candidate']=e.previous_event_type.notna()&(e.interaction_change|e.app_change|e.window_change|e.browser_context_change|(e.gap_seconds>1)|e.event_type.isin(['clipboard_change','browser_navigation','browser_form_input']));vocab=e.event_type.value_counts().head(18).index.tolist();c=pd.concat([features(s,s.index[s.candidate],vocab) for _,s in e.groupby('session_id',sort=False)],ignore_index=True);c['true_boundary']=e.loc[c.row_id,'true_boundary'].to_numpy();c['gt_execution_id']=e.loc[c.row_id,'execution_id'].to_numpy()
sids=sorted(e.session_id.unique());hold=set(sids[::5]);tr=c[~c.session_id.isin(hold)].copy();drop={'row_id','session_id','timestamp_iso','event_index','true_boundary','gt_execution_id'};fs=[x for x in c if x not in drop and c[x].dtype!=object]
oof=[]
for fi,vi in GroupKFold(n_splits=5).split(tr,tr.true_boundary,groups=tr.session_id):
 m=make_pipeline(StandardScaler(),LogisticRegression(class_weight='balanced',max_iter=1000,random_state=41));m.fit(tr.iloc[fi][fs],tr.iloc[fi].true_boundary);x=tr.iloc[vi].copy();x['score']=m.predict_proba(x[fs])[:,1];oof.append(x)
oof=pd.concat(oof,ignore_index=True);sweep=[]
for t in np.arange(.05,.951,.01):
 p=oof.row_id.isin(select(oof,t)).astype(int);a,b,d=metrics(oof.true_boundary,p);sweep.append((round(float(t),2),a,b,d,int(p.sum())))
cal=pd.DataFrame(sweep,columns=['threshold','precision','recall','f1','predicted_boundaries']);cal.to_csv(O/'calibration_curve.csv',index=False);best=sorted(sweep,key=lambda x:(x[3],x[0]),reverse=True)[0];threshold=best[0]
m=make_pipeline(StandardScaler(),LogisticRegression(class_weight='balanced',max_iter=1000,random_state=41));m.fit(tr[fs],tr.true_boundary);c['score']=m.predict_proba(c[fs])[:,1];picked=select(c,threshold);c['predicted_boundary']=c.row_id.isin(picked).astype(int);c['split']=np.where(c.session_id.isin(hold),'heldout','training');c['result']=np.select([(c.true_boundary==1)&(c.predicted_boundary==1),(c.true_boundary==0)&(c.predicted_boundary==1),c.true_boundary==1],['TP','FP','FN_candidate'],default='TN')
miss=e[(e.true_boundary==1)&~e.index.isin(c.row_id)];add=pd.DataFrame({'row_id':miss.index,'session_id':miss.session_id,'timestamp_iso':miss.timestamp_iso,'event_index':miss.event_index,'true_boundary':1,'score':np.nan,'predicted_boundary':0,'split':np.where(miss.session_id.isin(hold),'heldout','training'),'result':'FN_not_candidate'});b=pd.concat([c,add],ignore_index=True,sort=False).sort_values(['session_id','event_index']);b.to_csv(O/'boundary_results.csv',index=False)
segs=[]
for sid,s in e.groupby('session_id',sort=False):
 cuts=sorted(set(s.index)&picked);starts=[s.index[0]]+cuts;ends=[i-1 for i in cuts]+[s.index[-1]]
 for n,(a,z) in enumerate(zip(starts,ends),1):
  x=s.loc[a:z];segs.append({'session_id':sid,'segment_number':n,'start_timestamp':x.timestamp_iso.iloc[0],'end_timestamp':x.timestamp_iso.iloc[-1],'duration_seconds':max(0,(x.timestamp_ms.iloc[-1]-x.timestamp_ms.iloc[0])/1000),'event_count':len(x),'start_chunk_id':x.chunk_id.iloc[0],'end_chunk_id':x.chunk_id.iloc[-1],'crosses_chunk':x.chunk_id.nunique()>1,'handling':'continuation_across_chunk' if x.chunk_id.nunique()>1 else 'within_chunk','gt_execution_count':x.execution_id.dropna().nunique(),'gt_primary_execution_id':x.execution_id.dropna().mode().iloc[0] if x.execution_id.notna().any() else None})
seg=pd.DataFrame(segs);seg.to_csv(O/'segment_results.csv',index=False)
stats=[];sr=[]
for scope,x in [('heldout',b[b.split=='heldout']),('all_dataset_a',b)]:
 a,d,f=metrics(x.true_boundary,x.predicted_boundary);ss=seg[seg.session_id.isin(x.session_id.unique())];gt=int(x.true_boundary.sum());pr=int(x.predicted_boundary.sum());stats += [{'scope':scope,'metric':'boundary_precision','value':a},{'scope':scope,'metric':'boundary_recall','value':d},{'scope':scope,'metric':'boundary_f1','value':f},{'scope':scope,'metric':'predicted_boundary_count','value':pr},{'scope':scope,'metric':'gt_boundary_count','value':gt},{'scope':scope,'metric':'boundary_count_difference_pred_minus_gt','value':pr-gt},{'scope':scope,'metric':'predicted_segments','value':len(ss)},{'scope':scope,'metric':'median_segment_duration_seconds','value':ss.duration_seconds.median()},{'scope':scope,'metric':'mean_segment_duration_seconds','value':ss.duration_seconds.mean()},{'scope':scope,'metric':'segments_crossing_chunk','value':int(ss.crosses_chunk.sum())}]
for sid,x in b.groupby('session_id'):
 a,d,f=metrics(x.true_boundary,x.predicted_boundary);ss=seg[seg.session_id==sid];sr.append({'session_id':sid,'split':x.split.iloc[0],'gt_boundaries':int(x.true_boundary.sum()),'predicted_boundaries':int(x.predicted_boundary.sum()),'boundary_precision':a,'boundary_recall':d,'boundary_f1':f,'over_under_segmented':int(x.predicted_boundary.sum()-x.true_boundary.sum()),'predicted_segments':len(ss),'median_segment_duration_seconds':ss.duration_seconds.median(),'cross_chunk_segments':int(ss.crosses_chunk.sum())})
st=pd.DataFrame(stats);st.to_csv(O/'segmentation_statistics.csv',index=False);pd.DataFrame(sr).to_csv(O/'session_results.csv',index=False)
ex=[]
for lab in ['TP','FP','FN_candidate','FN_not_candidate']:
 for _,r in b[b.result==lab].sort_values('score',ascending=(lab!='TP')).head(20).iterrows():
  s=e[e.session_id==r.session_id];pre=context(s,int(r.row_id),'pre');post=context(s,int(r.row_id),'post');ex.append({'result':lab,'session_id':r.session_id,'timestamp_iso':r.timestamp_iso,'score':r.score,'event_index':r.event_index,'pre_event_types':pre[0],'post_event_types':post[0],'pre_apps':pre[1],'post_apps':post[1],'pre_windows':pre[2],'post_windows':post[2],'pre_text_or_clipboard':pre[3],'post_text_or_clipboard':post[3]})
pd.DataFrame(ex).to_csv(O/'boundary_examples.csv',index=False);pd.DataFrame({'feature':fs,'coefficient':m[-1].coef_[0]}).sort_values('coefficient',key=np.abs,ascending=False).head(20).to_csv(O/'scorer_feature_weights.csv',index=False)
print(json.dumps({'threshold':threshold,'training_oof_f1':best[3],'heldout':{r.metric:r.value for _,r in st[st.scope=='heldout'].iterrows()}},indent=2))

