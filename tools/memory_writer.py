import os
import json
from datetime import datetime, timezone

def append_jsonl(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\\n")

def write_run_scratchpad(base, run_id, event_type, payload):
    path = os.path.join(base, "scratchpad", f"{run_id}.jsonl")

    append_jsonl(path, {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload
    })
