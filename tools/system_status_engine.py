import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

FILES = {
    "Mobile Console App": BASE / "dashboard" / "mobile_console_app.py",
    "Decision Entry App": BASE / "dashboard" / "decision_entry_app.py",
    "Decision Replay App": BASE / "dashboard" / "decision_replay_app.py",
    "Decision Data Engine": BASE / "tools" / "decision_data_engine.py",
    "Decision Replay Engine": BASE / "tools" / "decision_replay_engine.py",
    "Decision Replay Interpreter": BASE / "tools" / "decision_replay_interpreter.py",
    "Decision Journal Writer": BASE / "tools" / "decision_journal_writer.py",
    "Start Launcher": BASE / "start_hermes_apps.ps1",
    "Stop Launcher": BASE / "stop_hermes_apps.ps1",
    "Decision Data Status": BASE / "features" / "latest_decision_data_status.json",
    "Decision Replay": BASE / "features" / "latest_decision_replay.json",
    "Decision Replay Interpretation": BASE / "features" / "latest_decision_replay_interpretation.json",
    "Market Console Trends": BASE / "features" / "latest_market_console_trends.json",
    "Batch Replay CSV": BASE / "data" / "replay_price_updates.csv",
    "Manual Actions Journal": BASE / "data" / "manual_actions_journal.jsonl",
    "Agent Suggestions Journal": BASE / "data" / "agent_suggestions_journal.jsonl",
    "Thesis Health Journal": BASE / "data" / "thesis_health_journal.jsonl",
    "Portfolio Snapshot": BASE / "data" / "portfolio_snapshot.json",
}

DECISION_STATUS = BASE / "features" / "latest_decision_data_status.json"
REPLAY_STATUS = BASE / "features" / "latest_decision_replay.json"
REPLAY_INTERPRETATION = BASE / "features" / "latest_decision_replay_interpretation.json"
MARKET_TRENDS = BASE / "features" / "latest_market_console_trends.json"

OUT_JSON = BASE / "features" / "latest_system_status.json"
OUT_MD = BASE / "reports" / "daily" / "latest_system_status.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def file_status():
    rows = []
    for name, path in FILES.items():
        rows.append({
            "name": name,
            "exists": path.exists(),
            "path": str(path),
        })
    return rows


def summarize():
    files = file_status()
    missing_files = [x["name"] for x in files if not x["exists"]]

    decision = load_json(DECISION_STATUS, {})
    replay = load_json(REPLAY_STATUS, {})
    interpretation_packet = load_json(REPLAY_INTERPRETATION, {})
    trends = load_json(MARKET_TRENDS, {})

    decision_status = decision.get("overall_status", "not_run")
    decision_counts = decision.get("counts", {})

    replay_summary = replay.get("summary", {})
    replay_status = replay_summary.get("overall_status", "not_run")
    missing_prices = replay.get("tickers_missing_current_price", [])

    interpretation = interpretation_packet.get("interpretation", {})
    replay_headline = interpretation.get("headline", "Replay interpretation has not run yet.")
    replay_severity = interpretation.get("severity", "yellow")
    replay_next_actions = interpretation.get("next_actions", [])

    trend_count = trends.get("history_count", 0)

    blockers = []
    next_actions = []
    positives = []

    if not missing_files:
        positives.append("Core Hermes app, tool, data, and report files are present.")
    else:
        blockers.append("Missing required files: " + ", ".join(missing_files[:8]))
        next_actions.append("Regenerate or restore missing files before relying on full workflow.")

    if decision_status == "ready":
        positives.append("Decision data layer is ready.")
    else:
        blockers.append(f"Decision data layer status is {decision_status}.")
        for item in decision.get("missing", [])[:5]:
            next_actions.append(f"Fill missing decision data: {item}.")

    if replay_status in ["ready", "partial"]:
        positives.append(f"Decision replay status is {replay_status}.")
    else:
        blockers.append(f"Decision replay status is {replay_status}.")

    if missing_prices:
        blockers.append("Current prices are missing for: " + ", ".join(missing_prices))
        for ticker in missing_prices:
            next_actions.append(f"Update current price for {ticker} in Decision Entry.")

    if replay_next_actions:
        for item in replay_next_actions[:5]:
            if item not in next_actions:
                next_actions.append(item)

    if trend_count > 0:
        positives.append(f"Market Console trend history has {trend_count} snapshot(s).")
    else:
        blockers.append("Market Console trend history has no snapshots yet.")
        next_actions.append("Run market_console_trend_engine.py or click Refresh Trends.")

    manual_actions = decision_counts.get("manual_actions", 0)
    agent_suggestions = decision_counts.get("agent_suggestions", 0)
    thesis_records = decision_counts.get("thesis_records", 0)

    if manual_actions > 0:
        positives.append(f"Manual action journal has {manual_actions} record(s).")
    if agent_suggestions > 0:
        positives.append(f"Agent suggestion journal has {agent_suggestions} record(s).")
    if thesis_records > 0:
        positives.append(f"Thesis health journal has {thesis_records} record(s).")

    if replay_severity == "green" and not blockers:
        overall = "green"
        headline = "Hermes system is ready."
    elif len(blockers) <= 3:
        overall = "yellow"
        headline = "Hermes system is mostly ready, with a few blockers."
    else:
        overall = "red"
        headline = "Hermes system has important blockers."

    if not next_actions:
        next_actions.append("Continue normal workflow: review dashboard, log decisions, refresh replay, and monitor trends.")

    return {
        "timestamp": now_utc(),
        "overall": overall,
        "headline": headline,
        "positives": positives,
        "blockers": blockers,
        "next_actions": next_actions,
        "metrics": {
            "missing_files": len(missing_files),
            "decision_status": decision_status,
            "manual_actions": manual_actions,
            "agent_suggestions": agent_suggestions,
            "thesis_records": thesis_records,
            "replay_status": replay_status,
            "manual_ready": replay_summary.get("manual_ready_count", 0),
            "agent_ready": replay_summary.get("agent_ready_count", 0),
            "missing_current_prices": len(missing_prices),
            "market_trend_snapshots": trend_count,
        },
        "files": files,
        "source_reads": {
            "decision_status": str(DECISION_STATUS),
            "replay_status": str(REPLAY_STATUS),
            "replay_interpretation": str(REPLAY_INTERPRETATION),
            "market_trends": str(MARKET_TRENDS),
        }
    }


def main():
    payload = summarize()

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Hermes System Status")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append(f"## {payload['headline']}")
    lines.append("")
    lines.append(f"- Overall: {payload['overall']}")
    lines.append("")
    lines.append("## Metrics")
    for key, value in payload["metrics"].items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("## Positives")
    if payload["positives"]:
        for item in payload["positives"]:
            lines.append(f"- {item}")
    else:
        lines.append("- None yet.")

    lines.append("")
    lines.append("## Blockers")
    if payload["blockers"]:
        for item in payload["blockers"]:
            lines.append(f"- {item}")
    else:
        lines.append("- None.")

    lines.append("")
    lines.append("## Next Actions")
    for item in payload["next_actions"]:
        lines.append(f"- {item}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "overall": payload["overall"],
        "headline": payload["headline"],
        "json": str(OUT_JSON),
        "report": str(OUT_MD),
        "next_actions": payload["next_actions"][:5]
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
