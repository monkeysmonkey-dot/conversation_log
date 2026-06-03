import os
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
LEDGER = BASE / "execution" / "paper_orders.jsonl"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

def record_paper_signal(run_id, validation_result, market_data):
    trades = validation_result.get("validated_trades", [])

    written = []

    if not validation_result.get("approved_for_paper_trading", False):
        return {
            "written": False,
            "reason": "not_approved_for_paper_trading",
            "final_action": validation_result.get("final_action")
        }

    for t in trades:
        ticker = t.get("ticker", "")
        price = None

        try:
            price = market_data.get("price", {}).get(ticker, {}).get("price")
        except Exception:
            price = None

        row = {
            "timestamp": utc_now(),
            "run_id": run_id,
            "type": "paper_signal",
            "ticker": ticker,
            "side": t.get("side", ""),
            "confidence": t.get("confidence", 0.0),
            "allocation_pct": t.get("allocation_pct", 0.0),
            "reference_price": price,
            "final_action": validation_result.get("final_action"),
            "live_trading": False,
            "note": "Paper signal only. No broker order placed."
        }

        append_jsonl(LEDGER, row)
        written.append(row)

    return {
        "written": True,
        "count": len(written),
        "path": str(LEDGER)
    }
