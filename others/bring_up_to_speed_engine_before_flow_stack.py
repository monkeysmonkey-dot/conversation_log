import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

OUT_JSON = BASE / "features" / "latest_bring_up_to_speed.json"
OUT_MD = BASE / "reports" / "daily" / "latest_bring_up_to_speed.md"

TASKS = [
    ("FX Rates", "tools/fx_rate_engine.py"),
    ("Document Intake", "tools/document_intake_engine.py"),
    ("Document Router", "tools/document_router_engine.py"),
    ("Account Portfolio Sync", "tools/sync_account_portfolio_snapshot.py"),
    ("Price Verification", "tools/price_fallback_engine.py"),
    ("Decision Data", "tools/decision_data_engine.py"),
    ("Decision Replay", "tools/decision_replay_engine.py"),
    ("Decision Replay Interpreter", "tools/decision_replay_interpreter.py"),
    ("Market Console Trends", "tools/market_console_trend_engine.py"),
    ("Mutual Fund Analysis", "tools/mutual_fund_analysis_engine.py"),
    ("Mutual Fund Review Schedule", "tools/mutual_fund_review_scheduler.py"),
    ("Tax Advisor", "tools/tax_advisor_engine.py"),
    ("System Status", "tools/system_status_engine.py"),
]

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def run_task(name, rel_path):
    path = BASE / rel_path

    if not path.exists():
        return {
            "task": name,
            "status": "skipped",
            "reason": "tool missing"
        }

    try:
        kwargs = {
            "cwd": BASE,
            "capture_output": True,
            "text": True,
            "timeout": 300
        }

        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run([sys.executable, str(path)], **kwargs)

        return {
            "task": name,
            "status": "complete" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "reason": "ok" if result.returncode == 0 else (result.stderr or result.stdout)[-500:]
        }

    except Exception as e:
        return {
            "task": name,
            "status": "error",
            "reason": str(e)
        }

def main():
    results = [run_task(name, rel_path) for name, rel_path in TASKS]

    complete = len([r for r in results if r["status"] == "complete"])
    skipped = len([r for r in results if r["status"] == "skipped"])
    errors = len([r for r in results if r["status"] == "error"])

    payload = {
        "timestamp": now_utc(),
        "complete": complete,
        "skipped": skipped,
        "errors": errors,
        "results": results
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Bring Up To Speed")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Complete: {complete}")
    lines.append(f"- Skipped: {skipped}")
    lines.append(f"- Errors: {errors}")
    lines.append("")
    lines.append("## Tasks")
    for r in results:
        lines.append(f"- {r['task']}: {r['status']}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "complete": complete,
        "skipped": skipped,
        "errors": errors,
        "json": str(OUT_JSON)
    }, indent=2))

if __name__ == "__main__":
    main()
