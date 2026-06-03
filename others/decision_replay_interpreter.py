import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

REPLAY_PATH = BASE / "features" / "latest_decision_replay.json"
DECISION_STATUS_PATH = BASE / "features" / "latest_decision_data_status.json"

OUT_JSON = BASE / "features" / "latest_decision_replay_interpretation.json"
OUT_MD = BASE / "reports" / "daily" / "latest_decision_replay_interpretation.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def build_interpretation(replay, decision_status):
    summary = replay.get("summary", {})
    counts = replay.get("counts", {})
    missing_prices = replay.get("tickers_missing_current_price", [])
    manual_rows = replay.get("manual_replays", [])
    agent_rows = replay.get("agent_replays", [])

    status = summary.get("overall_status", "not_run")
    manual_ready = summary.get("manual_ready_count", 0)
    agent_ready = summary.get("agent_ready_count", 0)
    manual_missing = summary.get("manual_missing_count", 0)
    agent_missing = summary.get("agent_missing_count", 0)

    manual_count = counts.get("manual_actions", 0)
    agent_count = counts.get("agent_suggestions", 0)
    thesis_count = counts.get("thesis_records", 0)
    portfolio_positions = counts.get("portfolio_positions", 0)

    blockers = []
    next_actions = []
    positives = []

    if manual_count > 0:
        positives.append(f"Manual action journal has {manual_count} record(s).")
    else:
        blockers.append("No manual actions have been logged.")
        next_actions.append("Log at least one manual action from Decision Entry.")

    if agent_count > 0:
        positives.append(f"Agent suggestion journal has {agent_count} record(s).")
    else:
        blockers.append("No agent suggestions have been logged.")
        next_actions.append("Log at least one agent suggestion when the system produces a recommendation.")

    if thesis_count > 0:
        positives.append(f"Thesis health journal has {thesis_count} record(s).")
    else:
        blockers.append("No thesis health records have been logged.")
        next_actions.append("Add a thesis health update for active watchlist names.")

    if portfolio_positions > 0:
        positives.append(f"Portfolio snapshot has {portfolio_positions} position(s).")
    else:
        blockers.append("No portfolio snapshot/current price data is available.")
        next_actions.append("Add portfolio snapshot/current price data for tickers being replayed.")

    if missing_prices:
        blockers.append("Current price is missing for: " + ", ".join(missing_prices))
        for ticker in missing_prices:
            next_actions.append(f"Update portfolio snapshot/current price for {ticker}.")

    # Only evaluate the latest manual replay row per ticker.
    # Older test records with zero prices should not keep blocking the dashboard
    # after a corrected/latest record exists.
    latest_manual_by_ticker = {}
    for row in manual_rows:
        ticker = str(row.get("ticker", "")).upper()
        if ticker:
            latest_manual_by_ticker[ticker] = row

    zero_or_missing_reference = []
    for ticker, row in latest_manual_by_ticker.items():
        action_price = row.get("action_price")
        if action_price in [None, 0, 0.0]:
            zero_or_missing_reference.append(ticker)

    if zero_or_missing_reference:
        unique = sorted(set([x for x in zero_or_missing_reference if x]))
        blockers.append("Latest manual action record has missing or zero action price: " + ", ".join(unique))
        next_actions.append("Correct the latest manual reference/action price for affected tickers.")

    if manual_ready > 0:
        positives.append(f"{manual_ready} manual action(s) are replay-ready.")

    if agent_ready > 0:
        positives.append(f"{agent_ready} agent suggestion(s) are replay-ready.")

    if status == "partial":
        headline = "Decision replay is partially ready."
        severity = "yellow"
    elif status == "not_ready":
        headline = "Decision replay is not ready yet."
        severity = "red"
    elif status == "data_missing":
        headline = "Decision replay has insufficient data."
        severity = "red"
    elif status == "ready":
        headline = "Decision replay is ready."
        severity = "green"
    else:
        headline = "Decision replay status is unknown."
        severity = "yellow"

    if not next_actions:
        next_actions.append("Continue logging manual actions, agent suggestions, thesis updates, and portfolio snapshots.")

    return {
        "headline": headline,
        "severity": severity,
        "status": status,
        "plain_english_read": summary.get("read", "Replay engine has not produced a read yet."),
        "positives": positives,
        "blockers": blockers,
        "next_actions": next_actions,
        "metrics": {
            "manual_actions": manual_count,
            "agent_suggestions": agent_count,
            "thesis_records": thesis_count,
            "portfolio_positions": portfolio_positions,
            "manual_ready": manual_ready,
            "agent_ready": agent_ready,
            "manual_missing": manual_missing,
            "agent_missing": agent_missing,
            "missing_current_price_count": len(missing_prices)
        }
    }


def main():
    replay = load_json(REPLAY_PATH, {})
    decision_status = load_json(DECISION_STATUS_PATH, {})

    interpretation = build_interpretation(replay, decision_status)

    payload = {
        "timestamp": now_utc(),
        "interpretation": interpretation,
        "source_files": {
            "replay": str(REPLAY_PATH),
            "decision_status": str(DECISION_STATUS_PATH)
        },
        "outputs": {
            "json": str(OUT_JSON),
            "report": str(OUT_MD)
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Decision Replay Interpretation")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append(f"## {interpretation['headline']}")
    lines.append("")
    lines.append(f"- Severity: {interpretation['severity']}")
    lines.append(f"- Status: {interpretation['status']}")
    lines.append(f"- Read: {interpretation['plain_english_read']}")
    lines.append("")
    lines.append("## Metrics")
    for key, value in interpretation["metrics"].items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("## Positives")
    if interpretation["positives"]:
        for item in interpretation["positives"]:
            lines.append(f"- {item}")
    else:
        lines.append("- None yet.")

    lines.append("")
    lines.append("## Blockers")
    if interpretation["blockers"]:
        for item in interpretation["blockers"]:
            lines.append(f"- {item}")
    else:
        lines.append("- None.")

    lines.append("")
    lines.append("## Next Actions")
    for item in interpretation["next_actions"]:
        lines.append(f"- {item}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "headline": interpretation["headline"],
        "severity": interpretation["severity"],
        "json": str(OUT_JSON),
        "report": str(OUT_MD),
        "next_actions": interpretation["next_actions"][:5]
    }, indent=2))


if __name__ == "__main__":
    main()
