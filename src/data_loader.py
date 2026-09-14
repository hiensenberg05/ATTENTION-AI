"""Dataset discovery without hard-coded session or chunk counts."""
from pathlib import Path

def discover_dataset(root):
    root = Path(root); sessions = []
    for session_path in sorted(p for p in root.glob('ses_*') if p.is_dir()):
        chunks = [{'chunk_id': p.name, 'path': p, 'events_path': p/'events.jsonl', 'manifest_path': p/'manifest.json', 'screenshots_path': p/'screenshots'} for p in sorted(session_path.glob('chunk_*')) if p.is_dir()]
        sessions.append({'session_id': session_path.name, 'path': session_path, 'chunks': chunks, 'gt_path': session_path/'gt.jsonl', 'gt_manifest_path': session_path/'gt_manifest.json'})
    return sessions

def iter_event_files(dataset):
    for session in dataset:
        for chunk in session['chunks']:
            yield session, chunk
