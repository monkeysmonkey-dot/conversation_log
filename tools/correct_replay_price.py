import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

PORTFOLIO_SNAPSHOT = BASE / "data" / "portfolio_snapshot.json"
MANUAL_ACTIONS = BASE / "data" / "manual_actions_journal.jsonl"
AGENT_SUGGESTIONS = BASE / "data" / "agent_suggestions_journal.jsonl"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def refresh():
    commands = [
        ["py", "tools\\decision_data_engine.py"],
        ["py", "tools\\decision_replay_engine.py"],
        ["py", "tools\\decision_replay_interpreter.py"],
        ["py", "tools\\system_status_engine.py"],
    ]

    results = []
    for cmd in commands:
        r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=180)
        results.append({
            "command": " ".join(cmd),
            "status": "complete" if r.returncode == 0 else "error"
        })
    return results


def main():
    parser = argparse.ArgumentParser(description="Correct replay prices by adding corrected latest records.")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--current-price", type=float, required=True)
    parser.add_argument("--reference-price", type=float, required=True)
    parser.add_argument("--reason", default="Corrected replay price entry")
    parser.add_argument("--update-agent", action="store_true")
    args = parser.parse_args()

    ticker = args.ticker.upper()

    portfolio = load_json(PORTFOLIO_SNAPSHOT, {})
    portfolio.setdefault("positions", {})

    old = portfolio["positions"].get(ticker, {})

    portfolio["positions"][ticker] = {
        "ticker": ticker,
        "quantity": old.get("quantity", 0),
        "average_cost": old.get("average_cost", 0),
        "current_price": args.current_price,
        "market_value": old.get("market_value", 0),
        "unrealized_pnl": old.get("unrealized_pnl", 0),
        "notes": args.reason,
        "updated_at": now_utc(),
        "advisory_only": True
    }

    portfolio["updated_at"] = now_utc()
    portfolio["source"] = "correct_replay_price"
    portfolio["advisory_only"] = True

    save_json(PORTFOLIO_SNAPSHOT, portfolio)

    append_jsonl(MANUAL_ACTIONS, {
        "timestamp": now_utc(),
        "ticker": ticker,
        "action_type": "watch",
        "price": args.reference_price,
        "quantity": 0,
        "reason": args.reason,
        "notes": "Corrected latest replay reference price.",
        "tags": ["correction", "replay"],
        "source": "correct_replay_price",
        "advisory_only": True
    })

    if args.update_agent:
        append_jsonl(AGENT_SUGGESTIONS, {
            "timestamp": now_utc(),
            "ticker": ticker,
            "suggestion_type": "wait_for_confirmation",
            "reference_price": args.reference_price,
            "confidence": "medium",
            "agent": "correct_replay_price",
            "model": "manual_correction",
            "reason": args.reason,
            "notes": "Corrected latest agent replay reference price.",
            "tags": ["correction", "agent", "replay"],
            "source": "correct_replay_price",
            "advisory_only": True
        })

    refresh_results = refresh()

    print(json.dumps({
        "status": "complete",
        "ticker": ticker,
        "current_price": args.current_price,
        "reference_price": args.reference_price,
        "agent_updated": args.update_agent,
        "refresh": refresh_results
    }, indent=2))


if __name__ == "__main__":
    main()
