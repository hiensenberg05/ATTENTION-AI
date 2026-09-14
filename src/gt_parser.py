"""Ground-truth stream and manifest execution parsing."""
import json
from pathlib import Path

def read_gt_records(path):
    rows=[]
    for line_number,line in enumerate(Path(path).open(encoding='utf-8'),1):
        row=json.loads(line); row['raw_line_number']=line_number; rows.append(row)
    return rows

def manifest_executions(session_id,path):
    data=json.loads(Path(path).read_text(encoding='utf-8')); rows=[]
    for process in data.get('processes',[]):
        for e in process.get('executions',[]):
            rows.append({'session_id':session_id,'execution_id':e.get('exec_id'),'process_code':e.get('code') or process.get('code'),'process_name':process.get('family_name'),'domain':process.get('domain'),'variant':e.get('variant'),'case_id':e.get('case_id'),'start_ts':e.get('start_ts'),'end_ts':e.get('end_ts'),'apps_json':json.dumps(e.get('apps') or [],ensure_ascii=False),'phase':e.get('phase'),'seq':e.get('seq'),'split_id':e.get('split_id'),'continues_from_prev':e.get('continues_from_prev'),'continues_to_next':e.get('continues_to_next')})
    return rows
