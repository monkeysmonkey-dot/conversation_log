import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

ACCOUNT_PORTFOLIO = BASE / "data" / "account_portfolios.json"
PORTFOLIO_SNAPSHOT = BASE / "data" / "portfolio_snapshot.json"


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


def safe_float(value):
    try:
        if value in [None, ""]:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def main():
    account_data = load_json(ACCOUNT_PORTFOLIO, {"positions": []})
    positions = account_data.get("positions", [])

    snapshot = load_json(PORTFOLIO_SNAPSHOT, {})
    snapshot.setdefault("positions", {})

    grouped = {}

    for row in positions:
        account_group = row.get("account_group", "Stock Account")

        # Keep company retirement separate. Do not mix into stock replay cache.
        if account_group == "Company Retirement":
            continue

        ticker = str(row.get("ticker", "")).upper().strip()
        if not ticker:
            continue

        grouped.setdefault(ticker, {
            "ticker": ticker,
            "quantity": 0.0,
            "market_value": 0.0,
            "cost_basis": 0.0,
            "unrealized_pnl": 0.0,
            "current_price": 0.0,
            "security_currency": row.get("security_currency", "CAD"),
            "accounts": set(),
            "notes": []
        })

        quantity = safe_float(row.get("quantity"))
        current_price = safe_float(row.get("current_price_native"))
        average_cost = safe_float(row.get("average_cost_native"))
        market_value = safe_float(row.get("market_value_native"))
        cost_basis = safe_float(row.get("cost_basis_native"))
        unrealized_pnl = safe_float(row.get("unrealized_pnl_native"))

        if market_value == 0 and quantity and current_price:
            market_value = quantity * current_price

        if cost_basis == 0 and quantity and average_cost:
            cost_basis = quantity * average_cost

        if unrealized_pnl == 0:
            unrealized_pnl = market_value - cost_basis

        grouped[ticker]["quantity"] += quantity
        grouped[ticker]["market_value"] += market_value
        grouped[ticker]["cost_basis"] += cost_basis
        grouped[ticker]["unrealized_pnl"] += unrealized_pnl

        if current_price > 0:
            grouped[ticker]["current_price"] = current_price

        grouped[ticker]["security_currency"] = row.get("security_currency", grouped[ticker]["security_currency"])
        grouped[ticker]["accounts"].add(row.get("account_name", "Unknown"))

        note = row.get("notes", "")
        if note:
            grouped[ticker]["notes"].append(note)

    synced = []

    for ticker, item in grouped.items():
        quantity = item["quantity"]
        avg_cost = item["cost_basis"] / quantity if quantity else 0.0

        snapshot["positions"][ticker] = {
            "ticker": ticker,
            "quantity": quantity,
            "average_cost": round(avg_cost, 4),
            "current_price": round(item["current_price"], 4),
            "market_value": round(item["market_value"], 4),
            "unrealized_pnl": round(item["unrealized_pnl"], 4),
            "security_currency": item["security_currency"],
            "accounts": sorted(list(item["accounts"])),
            "notes": "Synced from Account Portfolio / Tax",
            "updated_at": now_utc(),
            "advisory_only": True
        }

        synced.append(ticker)

    snapshot["updated_at"] = now_utc()
    snapshot["source"] = "account_portfolio_tax_sync"
    snapshot["advisory_only"] = True

    save_json(PORTFOLIO_SNAPSHOT, snapshot)

    print(json.dumps({
        "status": "complete",
        "synced_tickers": synced,
        "excluded": "Company Retirement positions remain separate",
        "file": str(PORTFOLIO_SNAPSHOT)
    }, indent=2))


if __name__ == "__main__":
    main()
