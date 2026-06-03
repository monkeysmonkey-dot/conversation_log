import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

MANUAL_ACTIONS = BASE / "data" / "manual_actions_journal.jsonl"
AGENT_SUGGESTIONS = BASE / "data" / "agent_suggestions_journal.jsonl"
THESIS_HEALTH = BASE / "data" / "thesis_health_journal.jsonl"
PORTFOLIO_SNAPSHOT = BASE / "data" / "portfolio_snapshot.json"

OUT_JSON = BASE / "features" / "latest_decision_replay.json"
OUT_MD = BASE / "reports" / "daily" / "latest_decision_replay.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path):
    if not path.exists():
        return []

    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            if line.strip():
                rows.append(json.loads(line))
        except Exception:
            pass

    return rows


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_float(value):
    try:
        if value in [None, ""]:
            return None
        return float(value)
    except Exception:
        return None


def get_portfolio_positions():
    portfolio = load_json(PORTFOLIO_SNAPSHOT, {})
    positions = portfolio.get("positions", {})
    if not isinstance(positions, dict):
        return {}
    return positions


def current_price_for_ticker(ticker, positions):
    pos = positions.get(str(ticker).upper(), {})
    return safe_float(pos.get("current_price"))


def replay_manual_action(row, positions):
    ticker = str(row.get("ticker", "")).upper()
    action_price = safe_float(row.get("price"))
    current_price = current_price_for_ticker(ticker, positions)

    missing = []
    if not ticker:
        missing.append("ticker")
    if action_price is None:
        missing.append("action_price")
    if current_price is None:
        missing.append("current_price")

    replay_ready = len(missing) == 0

    movement_pct = None
    movement_abs = None

    if replay_ready and action_price != 0:
        movement_abs = round(current_price - action_price, 4)
        movement_pct = round(((current_price - action_price) / action_price) * 100, 2)

    return {
        "ticker": ticker,
        "timestamp": row.get("timestamp"),
        "action_type": row.get("action_type"),
        "action_price": action_price,
        "current_price": current_price,
        "replay_ready": replay_ready,
        "missing": missing,
        "movement_abs": movement_abs,
        "movement_pct": movement_pct,
        "reason": row.get("reason", ""),
        "notes": row.get("notes", "")
    }


def replay_agent_suggestion(row, positions):
    ticker = str(row.get("ticker", "")).upper()
    reference_price = safe_float(row.get("reference_price"))
    current_price = current_price_for_ticker(ticker, positions)

    missing = []
    if not ticker:
        missing.append("ticker")
    if reference_price is None:
        missing.append("reference_price")
    if current_price is None:
        missing.append("current_price")

    replay_ready = len(missing) == 0

    movement_pct = None
    movement_abs = None

    if replay_ready and reference_price != 0:
        movement_abs = round(current_price - reference_price, 4)
        movement_pct = round(((current_price - reference_price) / reference_price) * 100, 2)

    return {
        "ticker": ticker,
        "timestamp": row.get("timestamp"),
        "suggestion_type": row.get("suggestion_type"),
        "reference_price": reference_price,
        "current_price": current_price,
        "replay_ready": replay_ready,
        "missing": missing,
        "movement_abs": movement_abs,
        "movement_pct": movement_pct,
        "confidence": row.get("confidence", ""),
        "agent": row.get("agent", ""),
        "model": row.get("model", ""),
        "reason": row.get("reason", ""),
        "notes": row.get("notes", "")
    }


def latest_thesis_by_ticker(thesis_rows):
    latest = {}
    for row in thesis_rows:
        ticker = str(row.get("ticker", "")).upper()
        if ticker:
            latest[ticker] = row
    return latest


def summarize_replay(manual_replays, agent_replays):
    manual_ready = [x for x in manual_replays if x.get("replay_ready")]
    agent_ready = [x for x in agent_replays if x.get("replay_ready")]

    manual_missing = [x for x in manual_replays if not x.get("replay_ready")]
    agent_missing = [x for x in agent_replays if not x.get("replay_ready")]

    if not manual_replays and not agent_replays:
        overall = "data_missing"
        read = "No manual actions or agent suggestions have been logged yet."
    elif manual_ready or agent_ready:
        overall = "partial"
        read = "Some records are replay-ready. Missing price data still limits full replay analysis."
    else:
        overall = "not_ready"
        read = "Records exist, but replay cannot run until reference/action prices and current prices are available."

    return {
        "overall_status": overall,
        "read": read,
        "manual_ready_count": len(manual_ready),
        "agent_ready_count": len(agent_ready),
        "manual_missing_count": len(manual_missing),
        "agent_missing_count": len(agent_missing)
    }


def main():
    manual_rows = read_jsonl(MANUAL_ACTIONS)
    agent_rows = read_jsonl(AGENT_SUGGESTIONS)
    thesis_rows = read_jsonl(THESIS_HEALTH)
    positions = get_portfolio_positions()

    manual_replays = [replay_manual_action(row, positions) for row in manual_rows]
    agent_replays = [replay_agent_suggestion(row, positions) for row in agent_rows]

    thesis_latest = latest_thesis_by_ticker(thesis_rows)
    summary = summarize_replay(manual_replays, agent_replays)

    tickers_missing_current_price = sorted(list(set(
        item.get("ticker")
        for item in manual_replays + agent_replays
        if "current_price" in item.get("missing", []) and item.get("ticker")
    )))

    payload = {
        "timestamp": now_utc(),
        "summary": summary,
        "counts": {
            "manual_actions": len(manual_rows),
            "agent_suggestions": len(agent_rows),
            "thesis_records": len(thesis_rows),
            "portfolio_positions": len(positions)
        },
        "tickers_missing_current_price": tickers_missing_current_price,
        "manual_replays": manual_replays,
        "agent_replays": agent_replays,
        "latest_thesis_by_ticker": thesis_latest,
        "files": {
            "manual_actions": str(MANUAL_ACTIONS),
            "agent_suggestions": str(AGENT_SUGGESTIONS),
            "thesis_health": str(THESIS_HEALTH),
            "portfolio_snapshot": str(PORTFOLIO_SNAPSHOT),
            "json": str(OUT_JSON),
            "report": str(OUT_MD)
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Decision Replay Report")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Overall status: {summary['overall_status']}")
    lines.append(f"- Read: {summary['read']}")
    lines.append(f"- Manual replay-ready: {summary['manual_ready_count']}")
    lines.append(f"- Agent replay-ready: {summary['agent_ready_count']}")
    lines.append(f"- Manual missing: {summary['manual_missing_count']}")
    lines.append(f"- Agent missing: {summary['agent_missing_count']}")
    lines.append("")
    lines.append("## Counts")
    for key, value in payload["counts"].items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("## Tickers Missing Current Price")
    if tickers_missing_current_price:
        for ticker in tickers_missing_current_price:
            lines.append(f"- {ticker}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("## Manual Action Replay")
    if manual_replays:
        for item in manual_replays[-10:]:
            lines.append(
                f"- {item.get('ticker')} | {item.get('action_type')} | ready={item.get('replay_ready')} | "
                f"action_price={item.get('action_price')} | current_price={item.get('current_price')} | "
                f"move={item.get('movement_pct')}%"
            )
    else:
        lines.append("- No manual actions logged.")

    lines.append("")
    lines.append("## Agent Suggestion Replay")
    if agent_replays:
        for item in agent_replays[-10:]:
            lines.append(
                f"- {item.get('ticker')} | {item.get('suggestion_type')} | ready={item.get('replay_ready')} | "
                f"reference_price={item.get('reference_price')} | current_price={item.get('current_price')} | "
                f"move={item.get('movement_pct')}%"
            )
    else:
        lines.append("- No agent suggestions logged.")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "overall_status": summary["overall_status"],
        "json": str(OUT_JSON),
        "report": str(OUT_MD),
        "manual_ready": summary["manual_ready_count"],
        "agent_ready": summary["agent_ready_count"],
        "tickers_missing_current_price": tickers_missing_current_price
    }, indent=2))


if __name__ == "__main__":
    main()
