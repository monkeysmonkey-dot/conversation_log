import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

REVIEW = BASE / "data" / "portfolio_import_review.json"
PORTFOLIO = BASE / "data" / "portfolio_snapshot.json"
WATCHLIST = BASE / "data" / "watchlist_candidates.json"

OUT_JSON = BASE / "features" / "latest_portfolio_grouped_preview.json"
OUT_MD = BASE / "reports" / "daily" / "latest_portfolio_grouped_preview.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def safe_float(value):
    try:
        if value in [None, ""]:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def money(value):
    try:
        return round(float(value), 4)
    except Exception:
        return 0.0


def group_active_lots(lots):
    groups = {}

    for lot in lots:
        symbol = str(lot.get("symbol", "")).upper()
        account = str(lot.get("account_type", ""))
        source_account = str(lot.get("source_account_name", ""))
        currency = str(lot.get("currency", ""))
        key = (symbol, account, currency)

        groups.setdefault(key, {
            "symbol": symbol,
            "name": lot.get("name", ""),
            "account_type": account,
            "source_account_name": source_account,
            "currency": currency,
            "lots": [],
            "total_quantity": 0.0,
            "total_cost_basis": 0.0,
            "weighted_average_cost": 0.0,
            "needs_account_sorting": False,
            "transaction_dates": [],
            "source_files": set()
        })

        qty = safe_float(lot.get("quantity"))
        cost_basis = safe_float(lot.get("cost_basis"))

        groups[key]["lots"].append(lot)
        groups[key]["total_quantity"] += qty
        groups[key]["total_cost_basis"] += cost_basis

        if lot.get("needs_account_sorting"):
            groups[key]["needs_account_sorting"] = True

        if lot.get("transaction_date"):
            groups[key]["transaction_dates"].append(lot.get("transaction_date"))

        if lot.get("source_file"):
            groups[key]["source_files"].add(lot.get("source_file"))

    out = []

    for key, item in groups.items():
        qty = item["total_quantity"]
        total_cost = item["total_cost_basis"]
        item["weighted_average_cost"] = money(total_cost / qty) if qty else 0.0
        item["total_quantity"] = money(qty)
        item["total_cost_basis"] = money(total_cost)
        item["lot_count"] = len(item["lots"])
        item["first_transaction_date"] = min(item["transaction_dates"]) if item["transaction_dates"] else ""
        item["last_transaction_date"] = max(item["transaction_dates"]) if item["transaction_dates"] else ""
        item["source_files"] = sorted(list(item["source_files"]))

        if qty > 0:
            item["group_status"] = "active_holding"
        elif qty == 0 and item["lot_count"] > 0:
            item["group_status"] = "closed_or_zero_position"
        else:
            item["group_status"] = "unknown"

        out.append(item)

    return sorted(out, key=lambda x: (x.get("account_type", ""), x.get("symbol", "")))


def summarize_watchlist(candidates):
    by_symbol = {}

    for item in candidates:
        symbol = str(item.get("symbol", "")).upper()
        if not symbol:
            continue

        if symbol not in by_symbol:
            by_symbol[symbol] = {
                "symbol": symbol,
                "name": item.get("name", ""),
                "currency": item.get("currency", ""),
                "symbol_class": item.get("symbol_class", ""),
                "row_count": 0,
                "status": item.get("status", "pending_user_confirmation"),
                "reason": item.get("reason", "")
            }

        by_symbol[symbol]["row_count"] += int(item.get("row_count", 1) or 1)

    return sorted(by_symbol.values(), key=lambda x: x.get("symbol", ""))


def main():
    review = load_json(REVIEW, {
        "active_lots": [],
        "watchlist_candidates": [],
        "closed_history": [],
        "account_sorting_required": []
    })

    portfolio = load_json(PORTFOLIO, {})
    watch = load_json(WATCHLIST, {"watchlist_candidates": [], "closed_history": []})

    lots = review.get("active_lots", [])
    watchlist_candidates = watch.get("watchlist_candidates", review.get("watchlist_candidates", []))
    closed_history = watch.get("closed_history", review.get("closed_history", []))

    active_groups = group_active_lots(lots)
    watchlist_preview = summarize_watchlist(watchlist_candidates)

    account_sorting_groups = [
        item for item in active_groups
        if item.get("needs_account_sorting")
    ]

    payload = {
        "timestamp": now_utc(),
        "active_group_count": len(active_groups),
        "active_lot_count": len(lots),
        "watchlist_candidate_count": len(watchlist_preview),
        "closed_history_count": len(closed_history),
        "account_sorting_group_count": len(account_sorting_groups),
        "active_groups": active_groups,
        "watchlist_preview": watchlist_preview,
        "closed_history": closed_history,
        "account_sorting_groups": account_sorting_groups,
        "portfolio_positions_detected": len(portfolio.get("positions", {})) if isinstance(portfolio.get("positions", {}), dict) else 0,
        "advisory_only": True
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Portfolio Grouped Preview")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Active grouped holdings: {payload['active_group_count']}")
    lines.append(f"- Active lots: {payload['active_lot_count']}")
    lines.append(f"- Watchlist candidates: {payload['watchlist_candidate_count']}")
    lines.append(f"- Closed/history groups: {payload['closed_history_count']}")
    lines.append(f"- Groups needing tax-account sorting: {payload['account_sorting_group_count']}")
    lines.append(f"- Portfolio positions detected: {payload['portfolio_positions_detected']}")
    lines.append("")
    lines.append("## Active Holding Groups Preview")

    for item in active_groups[:120]:
        lines.append(
            f"- {item.get('symbol')} | {item.get('name')} | "
            f"Account: {item.get('account_type')} | Currency: {item.get('currency')} | "
            f"Qty: {item.get('total_quantity')} | Avg Cost: {item.get('weighted_average_cost')} | "
            f"Cost Basis: {item.get('total_cost_basis')} | Lots: {item.get('lot_count')} | "
            f"Needs Sorting: {item.get('needs_account_sorting')}"
        )

    lines.append("")
    lines.append("## Needs Tax-Account Sorting")

    if account_sorting_groups:
        for item in account_sorting_groups[:120]:
            lines.append(
                f"- {item.get('symbol')} | Qty: {item.get('total_quantity')} | "
                f"Currency: {item.get('currency')} | Source Account: {item.get('source_account_name')} | "
                f"Current: {item.get('account_type')}"
            )
    else:
        lines.append("- None.")

    lines.append("")
    lines.append("## Watchlist Candidates Preview")

    if watchlist_preview:
        for item in watchlist_preview[:120]:
            lines.append(
                f"- {item.get('symbol')} | {item.get('name')} | "
                f"Class: {item.get('symbol_class')} | Rows: {item.get('row_count')} | Status: {item.get('status')}"
            )
    else:
        lines.append("- None.")

    lines.append("")
    lines.append("## Closed / History Preview")

    if closed_history:
        for item in closed_history[:120]:
            lines.append(
                f"- {item.get('symbol')} | {item.get('name')} | Net shares: {item.get('net_shares')} | Status: {item.get('status')}"
            )
    else:
        lines.append("- None.")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "active_groups": payload["active_group_count"],
        "active_lots": payload["active_lot_count"],
        "watchlist_candidates": payload["watchlist_candidate_count"],
        "closed_history": payload["closed_history_count"],
        "account_sorting_groups": payload["account_sorting_group_count"],
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
