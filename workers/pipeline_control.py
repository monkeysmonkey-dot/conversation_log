import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
STATUS_PATH = BASE / "logs" / "manual_pipeline_status.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def run_command(name, cmd, timeout=900):
    try:
        r = subprocess.run(
            cmd,
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        result = {
            "name": name,
            "timestamp": utc_now(),
            "status": "complete" if r.returncode == 0 else "error",
            "returncode": r.returncode,
            "stdout_tail": r.stdout[-3000:],
            "stderr_tail": r.stderr[-3000:]
        }

    except Exception as e:
        result = {
            "name": name,
            "timestamp": utc_now(),
            "status": "failed",
            "error": str(e)
        }

    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    return result

def run_daily_system():
    return run_command(
        "daily_hermes_system",
        ["py", "run_hermes_system.py"],
        timeout=1200
    )

def run_theme_wave():
    return run_command(
        "theme_wave_engine",
        ["py", "tools\\theme_wave_engine.py"],
        timeout=600
    )

def run_weekend_research():
    return run_command(
        "weekend_research_pipeline",
        ["py", "run_weekend_research.py"],
        timeout=2400
    )

def load_last_status():
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
