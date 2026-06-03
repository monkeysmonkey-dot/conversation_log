import json
from pathlib import Path
from datetime import datetime, date

BASE = Path(__file__).resolve().parents[1]

OUT_JSON = BASE / "features" / "latest_platform_performance.json"
OUT_MD = BASE / "reports" / "daily" / "latest_platform_performance.md"

USAGE_LEDGER = BASE / "logs" / "ai_usage_ledger.jsonl"
MANUAL_ACTIONS = BASE / "data" / "manual_actions_journal.jsonl"
AGENT_SUGGESTIONS = BASE / "data" / "agent_suggestions_journal.jsonl"
PORTFOLIO_SNAPSHOT = BASE / "data" / "portfolio_snapshot.json"


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def today_iso():
    return date.today().isoformat()


def usage_today():
    if not USAGE_LEDGER.exists():
        return 0.0

    total = 0.0
    for line in USAGE_LEDGER.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            item = json.loads(line)
            ts = str(item.get("timestamp", ""))
            if ts.startswith(today_iso()):
                total += float(item.get("estimated_cost_usd", item.get("cost_usd", 0)) or 0)
        except Exception:
            pass
    return round(total, 4)


def count_jsonl(path):
    if not path.exists():
        return 0
    return len([x for x in path.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()])


def main():
    manual_count = count_jsonl(MANUAL_ACTIONS)
    suggestion_count = count_jsonl(AGENT_SUGGESTIONS)
    portfolio = load_json(PORTFOLIO_SNAPSHOT, {})

    missing = []
    if manual_count == 0:
        missing.append("manual_actions_journal.jsonl is empty or missing")
    if suggestion_count == 0:
        missing.append("agent_suggestions_journal.jsonl is empty or missing")
    if not portfolio:
        missing.append("portfolio_snapshot.json is missing")
    if not USAGE_LEDGER.exists():
        missing.append("ai_usage_ledger.jsonl is missing")

    ai_cost_today = usage_today()

    can_calculate_actual_pnl = manual_count > 0 and bool(portfolio)
    can_calculate_agent_replay = suggestion_count > 0 and bool(portfolio)
    can_calculate_roi = can_calculate_actual_pnl and ai_cost_today > 0

    if can_calculate_roi:
        roi_score = "calculable"
        roi_read = "Enough data exists to calculate platform ROI."
    else:
        roi_score = "data_missing"
        roi_read = "Platform ROI cannot be trusted yet because required action, suggestion, portfolio, or cost data is missing."

    layers = [
        {
            "layer": "Missing Data / P&L Readiness",
            "status": "needs_data" if missing else "ready",
            "what_works": "System can identify which data is missing.",
            "needs_improvement": "; ".join(missing) if missing else "No major missing data detected.",
            "next_step": "Start recording manual actions, agent suggestions, and portfolio snapshots."
        },
        {
            "layer": "Manual Action P&L",
            "status": "ready" if can_calculate_actual_pnl else "not_ready",
            "what_works": "Manual action P&L can be calculated only when trade/action timestamps and portfolio data exist.",
            "needs_improvement": "Need manual action journal and portfolio snapshot." if not can_calculate_actual_pnl else "Ready for P&L analytics.",
            "next_step": "Create/update data/manual_actions_journal.jsonl and data/portfolio_snapshot.json."
        },
        {
            "layer": "Agent Suggestion Replay",
            "status": "ready" if can_calculate_agent_replay else "not_ready",
            "what_works": "Can compare hypothetical outcome if agent suggestions were followed once suggestions and prices exist.",
            "needs_improvement": "Need agent suggestion journal and price/portfolio reference." if not can_calculate_agent_replay else "Ready for suggestion replay.",
            "next_step": "Start logging each agent suggestion with ticker, timestamp, suggested action type, and reference price."
        },
        {
            "layer": "Thesis Health Tracker",
            "status": "partial",
            "what_works": "Decision briefs can describe whether confirmation is improving or weakening.",
            "needs_improvement": "Need persistent thesis records by ticker with original thesis, invalidation rules, and evidence updates.",
            "next_step": "Create thesis_health_journal.jsonl."
        },
        {
            "layer": "Agentic Cost / ROI",
            "status": "ready" if ai_cost_today > 0 else "partial",
            "what_works": f"Local AI cost today is ${ai_cost_today}.",
            "needs_improvement": "Need reliable P&L and suggestion replay before profit/cost ROI is meaningful.",
            "next_step": "Connect actual/manual P&L and agent suggestion replay."
        },
        {
            "layer": "Agent Value Ranking",
            "status": "not_ready",
            "what_works": "Agent costs can eventually be compared against useful outcomes.",
            "needs_improvement": "Need per-agent suggestion outcomes, confidence, and cost attribution.",
            "next_step": "Log agent_id and model_id with each suggestion and task result."
        }
    ]

    payload = {
        "timestamp": datetime.now().isoformat(),
        "platform_roi_score": roi_score,
        "platform_roi_read": roi_read,
        "ai_cost_today_usd": ai_cost_today,
        "manual_action_count": manual_count,
        "agent_suggestion_count": suggestion_count,
        "missing_data": missing,
        "layers": layers
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("# Platform Performance / ROI")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append(f"- Platform ROI score: {roi_score}")
    lines.append(f"- Read: {roi_read}")
    lines.append(f"- AI cost today: ${ai_cost_today}")
    lines.append("")
    lines.append("## Layers")
    lines.append("")

    for layer in layers:
        lines.append(f"### {layer['layer']}")
        lines.append(f"- Status: {layer['status']}")
        lines.append(f"- What works: {layer['what_works']}")
        lines.append(f"- Needs improvement: {layer['needs_improvement']}")
        lines.append(f"- Next step: {layer['next_step']}")
        lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "json": str(OUT_JSON),
        "report": str(OUT_MD),
        "platform_roi_score": roi_score
    }, indent=2))


if __name__ == "__main__":
    main()
