import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

BASE = Path(__file__).resolve().parents[1]

REVIEW = BASE / "data" / "portfolio_import_review.json"
PORTFOLIO = BASE / "data" / "portfolio_snapshot.json"

OUT_JSON = BASE / "features" / "latest_portfolio_reconciliation.json"
OUT_MD = BASE / "reports" / "daily" / "latest_portfolio_reconciliation.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
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


def clean(value):
    return str(value or "").strip()


def tx_sign(tx_type, accounting):
    blob = f"{tx_type} {accounting}".lower()

    sell_terms = ["sell", "sold", "sale", "dispose", "disposed", "short sell"]
    buy_terms = ["buy", "bought", "purchase", "purchased", "reinvest", "dividend reinvest", "transfer in"]

    if any(x in blob for x in sell_terms):
        return -1

    if any(x in blob for x in buy_terms):
        return 1

    return 1


def group_lots(lots):
    grouped = defaultdict(list)

    for lot in lots:
        symbol = clean(lot.get("symbol")).upper()
        source_account = clean(lot.get("source_account_name"))
        account_type = clean(lot.get("account_type")) or "Needs Sorting"
        currency = clean(lot.get("currency")).upper()

        if not symbol:
            continue

        key = (symbol, source_account, account_type, currency)
        grouped[key].append(lot)

    return grouped


def reconcile_group(key, rows):
    symbol, source_account, account_type, currency = key

    # There are two possible interpretations:
    # 1. Shares Owned is already remaining/current shares per row/lot.
    # 2. Shares Owned is transaction quantity, and Type determines buy/sell sign.
    #
    # We calculate both and flag disagreement.
    sum_positive_qty = 0.0
    signed_net_qty = 0.0
    total_cost_positive = 0.0
    total_signed_cost = 0.0

    transaction_rows = []
    dates = []

    for row in rows:
        qty = safe_float(row.get("quantity"))
        cost = safe_float(row.get("average_cost"))
        cost_basis = safe_float(row.get("cost_basis"))
        tx_type = clean(row.get("transaction_type"))
        accounting = clean(row.get("accounting"))
        sign = tx_sign(tx_type, accounting)

        if qty != 0 or cost != 0 or cost_basis != 0:
            transaction_rows.append(row)

        if qty > 0:
            sum_positive_qty += qty
            total_cost_positive += cost_basis if cost_basis else qty * cost

        signed_qty = qty * sign
        signed_net_qty += signed_qty

        signed_cost = cost_basis if cost_basis else qty * cost
        total_signed_cost += signed_cost * sign

        if row.get("transaction_date"):
            dates.append(clean(row.get("transaction_date")))

    latest_date = max(dates) if dates else ""
    earliest_date = min(dates) if dates else ""

    # If any sell rows exist, signed net is usually more meaningful.
    has_sell = any(tx_sign(r.get("transaction_type"), r.get("accounting")) < 0 for r in rows)
    has_buy_or_sell_type = any(clean(r.get("transaction_type")) or clean(r.get("accounting")) for r in rows)

    if has_sell or has_buy_or_sell_type:
        preferred_qty = signed_net_qty
        preferred_method = "signed_transaction_net"
        preferred_cost = total_signed_cost
    else:
        preferred_qty = sum_positive_qty
        preferred_method = "sum_positive_remaining_shares"
        preferred_cost = total_cost_positive

    active = preferred_qty > 0

    if preferred_qty < 0:
        status = "needs_review_negative_net"
    elif active:
        status = "active_holding_candidate"
    elif transaction_rows:
        status = "closed_or_zero_position"
    else:
        status = "watchlist_only_no_position_data"

    avg_cost = preferred_cost / preferred_qty if preferred_qty > 0 else 0.0

    disagreement = abs(sum_positive_qty - signed_net_qty) > 0.0001

    confidence = "medium"
    if active and not disagreement:
        confidence = "high"
    elif disagreement:
        confidence = "needs_review"
    elif status == "closed_or_zero_position":
        confidence = "medium"

    return {
        "symbol": symbol,
        "source_account_name": source_account,
        "account_type": account_type,
        "currency": currency,
        "status": status,
        "active": active,
        "preferred_quantity": round(preferred_qty, 8),
        "preferred_average_cost": round(avg_cost, 8),
        "preferred_cost_basis": round(preferred_cost, 8),
        "preferred_method": preferred_method,
        "sum_positive_qty": round(sum_positive_qty, 8),
        "signed_net_qty": round(signed_net_qty, 8),
        "method_disagreement": disagreement,
        "confidence": confidence,
        "lot_count": len(rows),
        "transaction_rows": len(transaction_rows),
        "earliest_transaction_date": earliest_date,
        "latest_transaction_date": latest_date,
        "needs_account_sorting": any(bool(r.get("needs_account_sorting")) for r in rows),
        "lots": rows
    }


def build_reconciled_positions(groups, existing_positions):
    positions = {}

    if isinstance(existing_positions, dict):
        positions.update(existing_positions)

    active = []
    closed = []
    review = []
    watch = []

    for item in groups:
        if item["status"] == "active_holding_candidate":
            active.append(item)
        elif item["status"] == "closed_or_zero_position":
            closed.append(item)
        elif item["status"] == "watchlist_only_no_position_data":
            watch.append(item)
        else:
            review.append(item)

    for item in active:
        key = f"{item['symbol']}|{item['account_type']}|{item['currency']}"
        old = positions.get(key) or positions.get(item["symbol"], {})
        current_price = safe_float(old.get("current_price"))
        market_value = current_price * item["preferred_quantity"] if current_price else 0.0

        positions[key] = {
            **old,
            "ticker": item["symbol"],
            "symbol": item["symbol"],
            "account_type": item["account_type"],
            "source_account_name": item["source_account_name"],
            "currency": item["currency"],
            "quantity": item["preferred_quantity"],
            "average_cost": item["preferred_average_cost"],
            "cost_basis": item["preferred_cost_basis"],
            "current_price": current_price,
            "market_value": market_value,
            "lot_count": item["lot_count"],
            "lots": item["lots"],
            "needs_account_sorting": item["needs_account_sorting"],
            "reconciliation_method": item["preferred_method"],
            "reconciliation_confidence": item["confidence"],
            "source_type": "portfolio_reconciliation_agent",
            "updated_at": now_utc(),
            "advisory_only": True
        }

    return positions, active, closed, review, watch


def main():
    review_packet = load_json(REVIEW, {"active_lots": [], "watchlist_candidates": [], "closed_history": []})
    portfolio = load_json(PORTFOLIO, {})

    lots = review_packet.get("active_lots", [])

    grouped = group_lots(lots)
    reconciled_groups = [reconcile_group(key, rows) for key, rows in grouped.items()]
    reconciled_groups = sorted(reconciled_groups, key=lambda x: (x["account_type"], x["symbol"]))

    existing_positions = portfolio.get("positions", {})
    positions, active, closed, needs_review, watch = build_reconciled_positions(reconciled_groups, existing_positions)

    payload = {
        "timestamp": now_utc(),
        "status": "complete",
        "group_count": len(reconciled_groups),
        "active_candidates": len(active),
        "closed_or_zero": len(closed),
        "needs_review": len(needs_review),
        "watchlist_only": len(watch),
        "account_sorting_required": len([x for x in active if x.get("needs_account_sorting")]),
        "reconciled_groups": reconciled_groups,
        "active_candidates_detail": active,
        "closed_detail": closed,
        "needs_review_detail": needs_review,
        "watchlist_only_detail": watch,
        "positions_preview": positions,
        "advisory_only": True
    }

    save_json(OUT_JSON, payload)

    lines = []
    lines.append("# Portfolio Reconciliation Agent")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Groups analyzed: {payload['group_count']}")
    lines.append(f"- Active holding candidates: {payload['active_candidates']}")
    lines.append(f"- Closed / zero positions: {payload['closed_or_zero']}")
    lines.append(f"- Needs review: {payload['needs_review']}")
    lines.append(f"- Watchlist only: {payload['watchlist_only']}")
    lines.append(f"- Account sorting required: {payload['account_sorting_required']}")
    lines.append("")
    lines.append("## Active Holding Candidates")

    for item in active[:120]:
        lines.append(
            f"- {item['symbol']} | Qty {item['preferred_quantity']} | Avg Cost {item['preferred_average_cost']} | "
            f"Currency {item['currency']} | Account {item['account_type']} | Method {item['preferred_method']} | "
            f"Confidence {item['confidence']} | Needs sorting {item['needs_account_sorting']}"
        )

    lines.append("")
    lines.append("## Needs Review")

    if needs_review:
        for item in needs_review[:120]:
            lines.append(
                f"- {item['symbol']} | Status {item['status']} | Positive qty {item['sum_positive_qty']} | "
                f"Signed net {item['signed_net_qty']} | Confidence {item['confidence']}"
            )
    else:
        lines.append("- None.")

    lines.append("")
    lines.append("## Closed / Zero Positions")

    if closed:
        for item in closed[:120]:
            lines.append(f"- {item['symbol']} | Signed net {item['signed_net_qty']} | Lots {item['lot_count']}")
    else:
        lines.append("- None.")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "groups": payload["group_count"],
        "active_candidates": payload["active_candidates"],
        "closed_or_zero": payload["closed_or_zero"],
        "needs_review": payload["needs_review"],
        "account_sorting_required": payload["account_sorting_required"],
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
