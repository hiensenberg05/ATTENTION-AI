"""Run all approved Phase 0 transformations reproducibly. No segmentation is performed."""
from pathlib import Path
import json,sys
import pandas as pd
from src.data_loader import discover_dataset,iter_event_files
from src.event_parser import iter_events
from src.normalizer import normalize_event
from src.gt_parser import read_gt_records,manifest_executions
from src.gt_validator import validate_gt
from src.data_join import join_events_to_gt
from src.feature_builder import build_process_features

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs'; (OUT/'tables').mkdir(parents=True,exist_ok=True); (OUT/'profiles').mkdir(parents=True,exist_ok=True)
def events_frame(root):
    rows=[]; errors=[]
    for session,chunk in iter_event_files(discover_dataset(root)):
        if not chunk['events_path'].exists(): errors.append({'session_id':session['session_id'],'chunk_id':chunk['chunk_id'],'line_number':None,'error':'events.jsonl missing','raw_line':None}); continue
        for line,event,error in iter_events(chunk['events_path']):
            if error: errors.append({'session_id':session['session_id'],'chunk_id':chunk['chunk_id'],'line_number':line,**error})
            else: rows.append(normalize_event(event,chunk_id=chunk['chunk_id'],source_file=str(chunk['events_path'].relative_to(ROOT)),line_number=line))
    return pd.DataFrame(rows),pd.DataFrame(errors)
def profile(events,name):
    rows=[]
    for column in ['layer','event_type','active_app','process_name']:
        for value,count in events[column].fillna('<missing>').value_counts().items(): rows.append({'dataset':name,'metric':column,'value':value,'count':count})
    for column in ['active_app','window_title','browser_url','extracted_text','screenshot_filename']:
        rows.append({'dataset':name,'metric':'missingness','value':column,'count':int(events[column].isna().sum())})
    pd.DataFrame(rows).to_csv(OUT/'profiles'/f'{name}_profile.csv',index=False)
def main():
    a,a_errors=events_frame(ROOT/'dataset_a'); b,b_errors=events_frame(ROOT/'dataset_b'); a.to_parquet(OUT/'tables'/'dataset_a_events.parquet',index=False); b.to_parquet(OUT/'tables'/'dataset_b_events.parquet',index=False); pd.concat([a_errors.assign(dataset='a'),b_errors.assign(dataset='b')]).to_csv(OUT/'profiles'/'malformed_jsonl.csv',index=False); profile(a,'dataset_a');profile(b,'dataset_b')
    raw=[]; executions=[]
    for session in discover_dataset(ROOT/'dataset_a'):
        raw.extend([{'session_id':session['session_id'],**x} for x in read_gt_records(session['gt_path'])]); executions.extend(manifest_executions(session['session_id'],session['gt_manifest_path']))
    gt=pd.DataFrame(executions); raw_gt=pd.DataFrame(raw); validation=validate_gt(gt,raw_gt);
    for column in raw_gt.columns:
        if raw_gt[column].map(lambda value: isinstance(value, (dict, list))).any():
            raw_gt[column] = raw_gt[column].map(lambda value: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value)
    gt.to_parquet(OUT/'tables'/'dataset_a_gt_executions.parquet',index=False); raw_gt.to_parquet(OUT/'tables'/'dataset_a_gt_raw.parquet',index=False); validation.to_csv(OUT/'profiles'/'gt_validation.csv',index=False)
    joined=join_events_to_gt(a,gt); joined.to_parquet(OUT/'tables'/'dataset_a_events_with_gt.parquet',index=False); build_process_features(joined,gt).to_parquet(OUT/'tables'/'dataset_a_process_features.parquet',index=False)
    print(json.dumps({'dataset_a_events':len(a),'dataset_b_events':len(b),'gt_executions':len(gt),'gt_findings':len(validation),'malformed_events':len(a_errors)+len(b_errors)},indent=2))
if __name__=='__main__': main()

