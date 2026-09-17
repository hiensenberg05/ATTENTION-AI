import pandas as pd,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'phase1/results/phase1e_interaction_sequences';O.mkdir(exist_ok=True);(O/'plots').mkdir(exist_ok=True)
e=pd.read_parquet(R/'outputs/tables/dataset_a_events_with_gt.parquet').sort_values(['session_id','timestamp_ms','raw_line_number']).reset_index(drop=True);e['p']=e.groupby('session_id').execution_id.shift();e['b']=e.execution_id.notna()&e.p.notna()&e.execution_id.ne(e.p);e['prev']=e.groupby('session_id').event_type.shift();e['single_change']=e.event_type.ne(e.prev)
e['run_start']=e.single_change.astype(int);e['run_id']=e.groupby('session_id').run_start.cumsum();e['run_len']=e.groupby(['session_id','run_id']).event_type.transform('size');e['prev_run_len']=e.groupby('session_id').run_len.shift();e['run_boundary_change']=e.single_change&(e.run_len>=2)&(e.prev_run_len>=2);e['burst_change']=e.single_change&((e.run_len>=3)|(e.prev_run_len>=3));q=e[e.p.notna()];rows=[]
for c in ['single_change','run_boundary_change','burst_change']:
 rows.append({'signal':c,'boundary_recall':q[q.b][c].mean(),'candidate_count':int(q[c].sum()),'density':q[c].mean(),'false_positive_rate':q[~q.b][c].mean()})
d=pd.DataFrame(rows);d.to_csv(O/'sequence_signal_statistics.csv',index=False);q[q.b|q.run_boundary_change][['session_id','timestamp_iso','event_type','prev','b','run_len','prev_run_len','single_change','run_boundary_change','burst_change']].head(1000).to_csv(O/'boundary_examples.csv',index=False);print(d.to_string(index=False))
