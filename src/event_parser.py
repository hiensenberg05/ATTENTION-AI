"""Streaming JSONL parser that reports malformed records."""
import json
from pathlib import Path

def iter_events(path):
    with Path(path).open(encoding='utf-8') as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                item = json.loads(line)
                if not isinstance(item, dict): raise ValueError('JSON value is not an object')
                yield line_number, item, None
            except (json.JSONDecodeError, ValueError) as exc:
                yield line_number, None, {'error': str(exc), 'raw_line': line.rstrip('\n')}
