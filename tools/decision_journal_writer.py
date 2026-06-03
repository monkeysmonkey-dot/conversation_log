import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

MANUAL_ACTIONS = BASE / "data" / "manual_actions_journal.jsonl"
AGENT_SUGGESTIONS = BASE / "data" / "agent_suggestions_journal.jsonl"
THESIS_HEALTH = BASE / "data" / "thesis_health_journal.jsonl"
PORTFOLIO_SNAPSHOT = BASE / "data" / "portfolio_snapshot.json"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def split_tags(raw):
    if not raw:
        return []
    return [x.strip() for x in str(raw).split(",") if x.strip()]


def log_manual_action(args):
    row = {
        "timestamp": now_utc(),
        "ticker": args.ticker.upper(),
        "action_type": args.action_type,
        "price": args.price,
        "quantity": args.quantity,
        "reason": args.reason,
        "notes": args.notes,
        "tags": split_tags(args.tags),
        "source": "manual_user_entry",
        "advisory_only": True
    }
    append_jsonl(MANUAL_ACTIONS, row)
    return {
        "status": "complete",
        "type": "manual_action",
        "file": str(MANUAL_ACTIONS),
        "record": row
    }


def log_agent_suggestion(args):
    row = {
        "timestamp": now_utc(),
        "ticker": args.ticker.upper(),
        "suggestion_type": args.suggestion_type,
        "reference_price": args.reference_price,
        "confidence": args.confidence,
        "agent": args.agent,
        "model": args.model,
        "reason": args.reason,
        "notes": args.notes,
        "tags": split_tags(args.tags),
        "source": "agent_suggestion",
        "advisory_only": True
    }
    append_jsonl(AGENT_SUGGESTIONS, row)
    return {
        "status": "complete",
        "type": "agent_suggestion",
        "file": str(AGENT_SUGGESTIONS),
        "record": row
    }


def log_thesis_health(args):
    row = {
        "timestamp": now_utc(),
        "ticker": args.ticker.upper(),
        "thesis_status": args.thesis_status,
        "conviction": args.conviction,
        "supporting_evidence": args.supporting_evidence,
        "invalidating_evidence": args.invalidating_evidence,
        "notes": args.notes,
        "tags": split_tags(args.tags),
        "source": "manual_user_entry",
        "advisory_only": True
    }
    append_jsonl(THESIS_HEALTH, row)
    return {
        "status": "complete",
        "type": "thesis_health",
        "file": str(THESIS_HEALTH),
        "record": row
    }


def update_portfolio_snapshot(args):
    data = read_json(PORTFOLIO_SNAPSHOT, {})
    data.setdefault("positions", {})

    ticker = args.ticker.upper()

    data["positions"][ticker] = {
        "ticker": ticker,
        "quantity": args.quantity,
        "average_cost": args.average_cost,
        "current_price": args.current_price,
        "market_value": args.market_value,
        "unrealized_pnl": args.unrealized_pnl,
        "notes": args.notes,
        "updated_at": now_utc(),
        "advisory_only": True
    }

    data["updated_at"] = now_utc()
    data["source"] = "manual_user_entry"
    data["advisory_only"] = True

    write_json(PORTFOLIO_SNAPSHOT, data)

    return {
        "status": "complete",
        "type": "portfolio_snapshot",
        "file": str(PORTFOLIO_SNAPSHOT),
        "ticker": ticker
    }


def build_parser():
    parser = argparse.ArgumentParser(description="Decision journal writer.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("manual-action")
    p.add_argument("--ticker", required=True)
    p.add_argument("--action-type", required=True)
    p.add_argument("--price", type=float, default=None)
    p.add_argument("--quantity", type=float, default=None)
    p.add_argument("--reason", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--tags", default="")
    p.set_defaults(func=log_manual_action)

    p = sub.add_parser("agent-suggestion")
    p.add_argument("--ticker", required=True)
    p.add_argument("--suggestion-type", required=True)
    p.add_argument("--reference-price", type=float, default=None)
    p.add_argument("--confidence", default="")
    p.add_argument("--agent", default="")
    p.add_argument("--model", default="")
    p.add_argument("--reason", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--tags", default="")
    p.set_defaults(func=log_agent_suggestion)

    p = sub.add_parser("thesis-health")
    p.add_argument("--ticker", required=True)
    p.add_argument("--thesis-status", required=True)
    p.add_argument("--conviction", default="")
    p.add_argument("--supporting-evidence", default="")
    p.add_argument("--invalidating-evidence", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--tags", default="")
    p.set_defaults(func=log_thesis_health)

    p = sub.add_parser("portfolio-snapshot")
    p.add_argument("--ticker", required=True)
    p.add_argument("--quantity", type=float, default=None)
    p.add_argument("--average-cost", type=float, default=None)
    p.add_argument("--current-price", type=float, default=None)
    p.add_argument("--market-value", type=float, default=None)
    p.add_argument("--unrealized-pnl", type=float, default=None)
    p.add_argument("--notes", default="")
    p.set_defaults(func=update_portfolio_snapshot)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
