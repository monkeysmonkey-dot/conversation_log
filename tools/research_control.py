import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
STATUS_PATH = BASE / "logs" / "research_control_status.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def save_status(payload):
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

def load_research_status():
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def run_cmd(name, cmd, timeout=900):
    try:
        r = subprocess.run(
            cmd,
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        payload = {
            "timestamp": utc_now(),
            "name": name,
            "status": "complete" if r.returncode == 0 else "error",
            "returncode": r.returncode,
            "stdout_tail": r.stdout[-2000:],
            "stderr_tail": r.stderr[-2000:]
        }

    except Exception as e:
        payload = {
            "timestamp": utc_now(),
            "name": name,
            "status": "failed",
            "error": str(e)
        }

    save_status(payload)
    return payload

def run_macro_master():
    return run_cmd(
        "macro_master_pipeline",
        ["py", "tools\\macro_master_pipeline.py"],
        timeout=1200
    )

def generate_qualitative_queue():
    return run_cmd(
        "qualitative_research_queue",
        ["py", "tools\\qualitative_research_queue_runner.py"],
        timeout=600
    )

def open_one_source():
    return run_cmd(
        "open_one_qualitative_source",
        ["py", "tools\\qualitative_research_queue_runner.py", "--open-one"],
        timeout=120
    )

def open_selected_sources():
    return run_cmd(
        "open_selected_qualitative_sources",
        ["py", "tools\\qualitative_research_queue_runner.py", "--open-browser"],
        timeout=180
    )

def close_research_browser():
    return run_cmd(
        "close_research_browser",
        ["py", "tools\\browser_source_launcher.py", "--close"],
        timeout=120
    )

def browser_status():
    return run_cmd(
        "research_browser_status",
        ["py", "tools\\browser_source_launcher.py", "--status"],
        timeout=60
    )
