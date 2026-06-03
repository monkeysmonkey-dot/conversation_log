import csv
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

MANIFEST = BASE / "data" / "document_inbox" / "manifest.json"
ACCOUNT_MAP = BASE / "data" / "account_tax_map.json"
PORTFOLIO = BASE / "data" / "portfolio_snapshot.json"

OUT_JSON = BASE / "features" / "latest_portfolio_csv_import.json"
OUT_MD = BASE / "reports" / "daily" / "latest_portfolio_csv_import.md"
REVIEW_JSON = BASE / "data" / "portfolio_import_review.json"
WATCHLIST_JSON = BASE / "data" / "watchlist_candidates.json"


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


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def safe_float(value):
    try:
        text = clean(value).replace(",", "").replace("$", "")
        if text in ["", "-", "—", "None", "null"]:
            return 0.0
        return float(text)
    except Exception:
        return 0.0


def norm_key(value):
    return clean(value).lower().replace(" ", "_").replace("-", "_")


def first(row, names):
    normalized = {norm_key(k): v for k, v in row.items()}
    for name in names:
        key = norm_key(name)
        if key in normalized and clean(normalized[key]) != "":
            return normalized[key]
    return ""


def is_confirmed_portfolio_doc(doc):
    filename = clean(doc.get("filename")).lower()
    confirmed = doc.get("confirmed_designation", {}) or {}
    suggestion = doc.get("suggestion", {}) or {}

    blob = " ".join([
        filename,
        clean(confirmed.get("document_type")),
        clean(confirmed.get("destination")),
        clean(suggestion.get("document_type")),
        clean(suggestion.get("destination")),
    ]).lower()

    if not filename.endswith(".csv"):
        return False

    terms = ["portfolio", "holding", "holdings", "position", "positions", "portfolio update", "account balance", "brokerage"]
    return any(term in blob for term in terms)


def account_needs_sorting(account_name, account_map):
    generic = account_map.get("generic_account_names_requiring_sorting", [])
    generic_lower = [clean(x).lower() for x in generic]
    return clean(account_name).lower() in generic_lower


def classify_symbol(symbol):
    s = clean(symbol).upper()

    if not s:
        return "blank"

    if s.startswith("^"):
        return "index_or_benchmark"

    if "CASH" in s or s in ["USD", "CAD"]:
        return "cash_or_currency"

    return "security"


def selected_portfolio_csvs():
    manifest = load_json(MANIFEST, {"documents": []})
    docs = manifest.get("documents", [])
    selected = []

    for doc in docs:
        if is_confirmed_portfolio_doc(doc):
            p = Path(doc.get("path", ""))
            if not p.is_absolute():
                p = BASE / p
            if p.exists():
                selected.append((doc, p))

    return selected


def make_lot_id(symbol, account, currency, row_num, tx_date, tx_time, tx_type):
    return "|".join([
        clean(symbol).upper(),
        clean(account),
        clean(currency).upper(),
        clean(tx_date),
        clean(tx_time),
        clean(tx_type),
        str(row_num)
    ])


def parse_csv_grouped(path, account_map):
    raw_rows = []
    blank_rows = 0

    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)

        for row_num, raw in enumerate(reader, start=1):
            symbol = clean(first(raw, ["Symbol", "Display Symbol", "Ticker", "Security Symbol"]))
            name = clean(first(raw, ["Name", "Security Name", "Description", "Company Name"]))
            account = clean(first(raw, ["Portfolio", "Account", "Account Name", "Account Type"]))
            currency = clean(first(raw, ["Currency", "CCY"]))
            shares = safe_float(first(raw, ["Shares Owned", "Quantity", "Qty", "Shares", "Units"]))
            cost_per_share = safe_float(first(raw, ["Cost Per Share", "Average Cost", "Avg Cost", "Book Cost", "Cost Basis Per Share"]))
            commission = safe_float(first(raw, ["Commission"]))
            fx = safe_float(first(raw, ["Purchase Exchange Rate"]))
            tx_date = clean(first(raw, ["Transaction Date", "Date", "Purchase Date"]))
            tx_time = clean(first(raw, ["Transaction Time", "Time"]))
            tx_type = clean(first(raw, ["Type", "Transaction Type"]))
            accounting = clean(first(raw, ["Accounting"]))
            accounting_ids = clean(first(raw, ["Accounting Execution Ids"]))
            notes = clean(first(raw, ["Notes"]))

            if not symbol and not name:
                blank_rows += 1
                continue

            raw_rows.append({
                "row_num": row_num,
                "symbol": symbol.upper(),
                "name": name,
                "source_account_name": account,
                "currency": currency.upper(),
                "shares": shares,
                "cost_per_share": cost_per_share,
                "commission": commission,
                "purchase_exchange_rate": fx,
                "transaction_date": tx_date,
                "transaction_time": tx_time,
                "transaction_type": tx_type,
                "accounting": accounting,
                "accounting_execution_ids": accounting_ids,
                "notes": notes,
                "symbol_class": classify_symbol(symbol),
                "source_file": str(path)
            })

    groups = {}

    for r in raw_rows:
        key = (r["symbol"], r["source_account_name"], r["currency"])
        groups.setdefault(key, [])
        groups[key].append(r)

    active_lots = []
    closed_history = []
    watchlist_candidates = []

    for (symbol, account, currency), rows in groups.items():
        symbol_class = classify_symbol(symbol)

        rows_with_position_data = [
            r for r in rows
            if safe_float(r.get("shares")) != 0 or safe_float(r.get("cost_per_share")) != 0
        ]

        # If no row has any shares/cost, this is not an active position.
        # Treat normal securities as watchlist candidates, but keep indexes/cash separate.
        if not rows_with_position_data:
            representative = rows[0]

            watchlist_candidates.append({
                "symbol": symbol,
                "name": representative.get("name"),
                "account_source": account,
                "currency": currency,
                "symbol_class": symbol_class,
                "source_file": str(path),
                "row_count": len(rows),
                "reason": "No active quantity/cost found for this grouped symbol/account/currency.",
                "prompt_user": "No active position found. Add this item to watchlist?",
                "status": "pending_user_confirmation",
                "created_at": now_utc(),
                "advisory_only": True
            })
            continue

        # Use sum of shares across position-data rows.
        # This supports transaction-style CSVs where buys/sells are separate rows.
        net_shares = sum(safe_float(r.get("shares")) for r in rows_with_position_data)

        if net_shares <= 0:
            closed_history.append({
                "symbol": symbol,
                "name": rows[0].get("name"),
                "account_source": account,
                "currency": currency,
                "row_count": len(rows),
                "net_shares": net_shares,
                "status": "closed_or_zero_position",
                "reason": "Transaction rows exist, but net/current share count is zero or below.",
                "source_file": str(path),
                "updated_at": now_utc()
            })
            continue

        needs_sorting = account_needs_sorting(account, account_map)

        for r in rows_with_position_data:
            shares = safe_float(r.get("shares"))
            cost = safe_float(r.get("cost_per_share"))

            # Keep only rows contributing to active holding lots.
            if shares == 0 and cost == 0:
                continue

            cost_basis = shares * cost
            if safe_float(r.get("commission")):
                cost_basis += safe_float(r.get("commission"))

            active_lots.append({
                "lot_id": make_lot_id(symbol, account, currency, r.get("row_num"), r.get("transaction_date"), r.get("transaction_time"), r.get("transaction_type")),
                "symbol": symbol,
                "name": r.get("name"),
                "source_account_name": account,
                "account_type": "Needs Sorting" if needs_sorting else account,
                "needs_account_sorting": needs_sorting,
                "currency": currency,
                "quantity": shares,
                "average_cost": cost,
                "cost_basis": cost_basis,
                "commission": safe_float(r.get("commission")),
                "purchase_exchange_rate": safe_float(r.get("purchase_exchange_rate")),
                "transaction_date": r.get("transaction_date"),
                "transaction_time": r.get("transaction_time"),
                "transaction_type": r.get("transaction_type"),
                "accounting": r.get("accounting"),
                "accounting_execution_ids": r.get("accounting_execution_ids"),
                "notes": r.get("notes"),
                "source_file": str(path),
                "row_num": r.get("row_num"),
                "group_net_shares": net_shares,
                "source_type": "confirmed_portfolio_csv",
                "updated_at": now_utc(),
                "advisory_only": True
            })

    return {
        "active_lots": active_lots,
        "watchlist_candidates": watchlist_candidates,
        "closed_history": closed_history,
        "blank_rows": blank_rows,
        "groups_total": len(groups)
    }


def aggregate_positions(lots, existing_positions):
    positions = {}

    if isinstance(existing_positions, dict):
        positions.update(existing_positions)

    grouped = {}

    for lot in lots:
        key = (
            lot.get("symbol"),
            lot.get("account_type"),
            lot.get("currency")
        )
        grouped.setdefault(key, [])
        grouped[key].append(lot)

    for (symbol, account_type, currency), group in grouped.items():
        total_qty = sum(safe_float(x.get("quantity")) for x in group)
        total_cost = sum(safe_float(x.get("cost_basis")) for x in group)
        avg_cost = total_cost / total_qty if total_qty else 0.0

        # Keep account-separated position keys so one ticker can live in multiple accounts.
        position_key = f"{symbol}|{account_type}|{currency}"

        old = positions.get(position_key) or positions.get(symbol, {})
        current_price = safe_float(old.get("current_price"))
        market_value = current_price * total_qty if current_price else 0.0

        positions[position_key] = {
            **old,
            "ticker": symbol,
            "symbol": symbol,
            "account_type": account_type,
            "currency": currency,
            "quantity": total_qty,
            "average_cost": avg_cost,
            "cost_basis": total_cost,
            "current_price": current_price,
            "market_value": market_value,
            "lots": group,
            "lot_count": len(group),
            "needs_account_sorting": any(x.get("needs_account_sorting") for x in group),
            "source_type": "confirmed_portfolio_csv_grouped",
            "updated_at": now_utc(),
            "advisory_only": True
        }

    return positions


def main():
    account_map = load_json(ACCOUNT_MAP, {"generic_account_names_requiring_sorting": ["My Portfolio"]})
    files = selected_portfolio_csvs()

    all_lots = []
    all_watchlist = []
    all_closed = []
    files_used = []
    blank_total = 0
    group_total = 0

    for doc, path in files:
        try:
            parsed = parse_csv_grouped(path, account_map)

            all_lots.extend(parsed["active_lots"])
            all_watchlist.extend(parsed["watchlist_candidates"])
            all_closed.extend(parsed["closed_history"])
            blank_total += parsed["blank_rows"]
            group_total += parsed["groups_total"]

            files_used.append({
                "filename": doc.get("filename"),
                "path": str(path),
                "active_lots": len(parsed["active_lots"]),
                "watchlist_candidates": len(parsed["watchlist_candidates"]),
                "closed_history": len(parsed["closed_history"]),
                "blank_rows": parsed["blank_rows"],
                "groups_total": parsed["groups_total"]
            })

        except Exception as e:
            files_used.append({
                "filename": doc.get("filename"),
                "path": str(path),
                "error": str(e)
            })

    portfolio = load_json(PORTFOLIO, {})
    before_positions = len(portfolio.get("positions", {})) if isinstance(portfolio.get("positions", {}), dict) else 0
    before_lots = len(portfolio.get("lots", [])) if isinstance(portfolio.get("lots", []), list) else 0

    if all_lots:
        backup = PORTFOLIO.with_name("portfolio_snapshot_before_grouped_csv_import.json")
        if PORTFOLIO.exists():
            backup.write_text(PORTFOLIO.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")

        existing_positions = portfolio.get("positions", {})
        portfolio["lots"] = all_lots
        portfolio["positions"] = aggregate_positions(all_lots, existing_positions)
        portfolio["holdings"] = all_lots
        portfolio["closed_history"] = all_closed
        portfolio["updated_at"] = now_utc()
        portfolio["source"] = "portfolio_csv_import_engine_grouped"
        portfolio["advisory_only"] = True

        save_json(PORTFOLIO, portfolio)

    review = {
        "timestamp": now_utc(),
        "active_lots": all_lots,
        "watchlist_candidates": all_watchlist,
        "closed_history": all_closed,
        "account_sorting_required": [x for x in all_lots if x.get("needs_account_sorting")],
        "instructions": {
            "active_position_logic": "Grouped by symbol/account/currency. If grouped transaction rows have positive net shares, active lots are imported.",
            "watchlist_logic": "Groups with no share/cost evidence are pending watchlist confirmation, not active holdings.",
            "closed_history_logic": "Groups with transaction evidence but net shares <= 0 are stored as closed/history, not active holdings.",
            "account_sorting": "Generic account names require manual assignment to Taxable/Cash, TFSA, RRSP, FHSA, RESP, or Company Retirement."
        }
    }

    save_json(REVIEW_JSON, review)
    save_json(WATCHLIST_JSON, {
        "timestamp": now_utc(),
        "watchlist_candidates": all_watchlist,
        "closed_history": all_closed,
        "prompt_required": len(all_watchlist) > 0
    })

    after_positions = len(portfolio.get("positions", {})) if isinstance(portfolio.get("positions", {}), dict) else before_positions
    after_lots = len(portfolio.get("lots", [])) if isinstance(portfolio.get("lots", []), list) else before_lots

    payload = {
        "timestamp": now_utc(),
        "status": "complete",
        "files_used": files_used,
        "active_lots_imported": len(all_lots),
        "watchlist_candidates": len(all_watchlist),
        "closed_history": len(all_closed),
        "blank_rows": blank_total,
        "groups_total": group_total,
        "positions_before": before_positions,
        "positions_after": after_positions,
        "lots_before": before_lots,
        "lots_after": after_lots,
        "account_sorting_required": len(review["account_sorting_required"]),
        "portfolio_file": str(PORTFOLIO),
        "review_file": str(REVIEW_JSON),
        "watchlist_file": str(WATCHLIST_JSON),
        "advisory_only": True
    }

    save_json(OUT_JSON, payload)

    lines = []
    lines.append("# Portfolio CSV Import / Account Sorting")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Active lots imported: {payload['active_lots_imported']}")
    lines.append(f"- Watchlist candidates: {payload['watchlist_candidates']}")
    lines.append(f"- Closed/history positions: {payload['closed_history']}")
    lines.append(f"- Account sorting required: {payload['account_sorting_required']}")
    lines.append(f"- Blank rows skipped: {payload['blank_rows']}")
    lines.append(f"- Groups total: {payload['groups_total']}")
    lines.append(f"- Positions before: {payload['positions_before']}")
    lines.append(f"- Positions after: {payload['positions_after']}")
    lines.append(f"- Lots after: {payload['lots_after']}")
    lines.append("")
    lines.append("## Files Used")

    for f in files_used:
        lines.append(
            f"- {f.get('filename')} | active lots {f.get('active_lots')} | watchlist candidates {f.get('watchlist_candidates')} | closed/history {f.get('closed_history')} | blank rows {f.get('blank_rows')} | groups {f.get('groups_total')}"
        )

    lines.append("")
    lines.append("## Required User Prompts")

    if all_watchlist:
        lines.append("- Some grouped symbols have no active share/cost evidence. Prompt user to add selected symbols to watchlist.")
    if review["account_sorting_required"]:
        lines.append("- Some active lots use a generic account name and require manual tax-account sorting.")
    if all_closed:
        lines.append("- Some grouped symbols appear closed/history and should not be treated as active holdings.")

    if not all_watchlist and not review["account_sorting_required"] and not all_closed:
        lines.append("- No manual prompts required.")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "active_lots_imported": len(all_lots),
        "watchlist_candidates": len(all_watchlist),
        "closed_history": len(all_closed),
        "account_sorting_required": len(review["account_sorting_required"]),
        "positions_after": after_positions,
        "lots_after": after_lots,
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
