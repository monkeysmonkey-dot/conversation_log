import json
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

BASE = Path(__file__).resolve().parents[1]

USAGE_LEDGER = BASE / "logs" / "ai_usage_ledger.jsonl"
CONTROL_STATUS = BASE / "logs" / "control_center_status.json"
MODEL_CONFIG = BASE / "config" / "model_assignment_config.json"
SCHEDULE_CONFIG = BASE / "config" / "schedule_config.json"

OUT_JSON = BASE / "features" / "latest_model_performance_trends.json"
OUT_MD = BASE / "reports" / "daily" / "latest_model_performance_trends.md"


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def read_jsonl(path):
    if not Path(path).exists():
        return []

    rows = []
    for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            if line.strip():
                rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def today_iso():
    return date.today().isoformat()


def main():
    usage = read_jsonl(USAGE_LEDGER)
    status = load_json(CONTROL_STATUS, {})
    model_cfg = load_json(MODEL_CONFIG, {})
    schedule = load_json(SCHEDULE_CONFIG, {"tasks": []})

    global_model = model_cfg.get("global_default_model", "openrouter/auto")
    assignments = model_cfg.get("model_assignments", {})

    task_labels = {
        t.get("id"): t.get("label", t.get("id"))
        for t in schedule.get("tasks", [])
        if t.get("id")
    }

    by_task = defaultdict(lambda: {
        "runs": 0,
        "cost_usd": 0.0,
        "models": defaultdict(lambda: {
            "runs": 0,
            "cost_usd": 0.0
        })
    })

    total_cost_today = 0.0

    for row in usage:
        ts = str(row.get("timestamp", ""))
        task_id = row.get("task_id") or row.get("task") or row.get("name") or "unknown"
        model = row.get("model") or row.get("model_id") or assignments.get(task_id, global_model)
        cost = float(row.get("estimated_cost_usd", row.get("cost_usd", 0)) or 0)

        by_task[task_id]["runs"] += 1
        by_task[task_id]["cost_usd"] += cost
        by_task[task_id]["models"][model]["runs"] += 1
        by_task[task_id]["models"][model]["cost_usd"] += cost

        if ts.startswith(today_iso()):
            total_cost_today += cost

    runs = status.get("runs", {})

    task_summary = []

    for task_id, label in task_labels.items():
        assigned_model = assignments.get(task_id)
        effective_model = assigned_model or global_model
        task_usage = by_task.get(task_id, {
            "runs": 0,
            "cost_usd": 0.0,
            "models": {}
        })

        last_run = runs.get(task_id, {})
        last_status = last_run.get("status", "not_run")

        model_breakdown = []
        for model, mdata in task_usage.get("models", {}).items():
            model_breakdown.append({
                "model": model,
                "runs": mdata.get("runs", 0),
                "cost_usd": round(mdata.get("cost_usd", 0.0), 4)
            })

        model_breakdown = sorted(model_breakdown, key=lambda x: x["cost_usd"], reverse=True)

        if task_usage.get("runs", 0) == 0:
            performance_read = "No enough run/cost history yet. Needs more data."
            status_read = "data_missing"
        elif last_status == "complete":
            performance_read = "Task has completed with current/assigned model history."
            status_read = "working"
        else:
            performance_read = "Task has run history but last status is not complete. Review logs."
            status_read = "needs_review"

        task_summary.append({
            "task_id": task_id,
            "label": label,
            "assigned_model": assigned_model,
            "effective_model": effective_model,
            "uses_default_model": assigned_model in [None, ""],
            "runs": task_usage.get("runs", 0),
            "cost_usd": round(task_usage.get("cost_usd", 0.0), 4),
            "last_status": last_status,
            "status_read": status_read,
            "performance_read": performance_read,
            "model_breakdown": model_breakdown
        })

    payload = {
        "timestamp": datetime.now().isoformat(),
        "global_default_model": global_model,
        "total_cost_today_usd": round(total_cost_today, 4),
        "task_summary": task_summary,
        "interpretation": {
            "what_works": "Model performance trend can track task/model/cost once task usage is logged.",
            "needs_improvement": "To evaluate model quality, each task result should log model_id, task_id, cost, status, and a quality score.",
            "next_step": "Add quality scoring per task output: useful / not useful / needs review / caused error."
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("# Model Performance Trends")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Global default model: {global_model}")
    lines.append(f"- Total cost today: ${payload['total_cost_today_usd']}")
    lines.append("")
    lines.append("## Task Summary")
    lines.append("")

    for t in task_summary:
        lines.append(f"### {t['label']}")
        lines.append(f"- Effective model: {t['effective_model']}")
        lines.append(f"- Uses default: {t['uses_default_model']}")
        lines.append(f"- Runs: {t['runs']}")
        lines.append(f"- Cost: ${t['cost_usd']}")
        lines.append(f"- Last status: {t['last_status']}")
        lines.append(f"- Read: {t['performance_read']}")
        lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "json": str(OUT_JSON),
        "report": str(OUT_MD),
        "task_count": len(task_summary)
    }, indent=2))


if __name__ == "__main__":
    main()
