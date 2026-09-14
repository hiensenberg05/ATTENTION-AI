"""Second deterministic Phase 0 build stage: GT, temporal join, and features."""
from pathlib import Path
import json
import pandas as pd
from src.data_loader import discover_dataset
from src.gt_parser import read_gt_records,manifest_executions
from src.gt_validator import validate_gt
from src.data_join import join_events_to_gt
from src.feature_builder import build_process_features
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs'
def main():
    raw=[]; executions=[]
    for session in discover_dataset(ROOT/'dataset_a'):
        raw.extend([{'session_id':session['session_id'],**x} for x in read_gt_records(session['gt_path'])]); executions.extend(manifest_executions(session['session_id'],session['gt_manifest_path']))
    gt=pd.DataFrame(executions); raw_gt=pd.DataFrame(raw); validation=validate_gt(gt,raw_gt)
    for col in raw_gt.columns:
        if raw_gt[col].map(lambda x:isinstance(x,(dict,list))).any(): raw_gt[col]=raw_gt[col].map(lambda x:json.dumps(x,ensure_ascii=False) if isinstance(x,(dict,list)) else x)
    gt.to_parquet(OUT/'tables'/'dataset_a_gt_executions.parquet',index=False); raw_gt.to_parquet(OUT/'tables'/'dataset_a_gt_raw.parquet',index=False); validation.to_csv(OUT/'profiles'/'gt_validation.csv',index=False)
    events=pd.read_parquet(OUT/'tables'/'dataset_a_events.parquet'); joined=join_events_to_gt(events,gt); joined.to_parquet(OUT/'tables'/'dataset_a_events_with_gt.parquet',index=False); features=build_process_features(joined,gt); features.to_parquet(OUT/'tables'/'dataset_a_process_features.parquet',index=False)
    print({'gt_executions':len(gt),'raw_gt_records':len(raw_gt),'validation_findings':len(validation),'assigned_events':int(joined.gt_assignment.eq('assigned').sum()),'features':len(features)})
if __name__=='__main__': main()
