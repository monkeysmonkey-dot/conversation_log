import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

ACCOUNT_PORTFOLIO = BASE / "data" / "account_portfolios.json"
FX_RATES = BASE / "features" / "latest_fx_rates.json"
THESIS_HEALTH = BASE / "data" / "thesis_health_journal.jsonl"
MUTUAL_FUND_RESEARCH = BASE / "data" / "mutual_fund_research.json"

OUT_JSON = BASE / "features" / "latest_tax_advisor.json"
OUT_MD = BASE / "reports" / "daily" / "latest_tax_advisor.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


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


def safe_float(value):
    try:
        if value in [None, ""]:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def latest_thesis_by_ticker():
    rows = read_jsonl(THESIS_HEALTH)
    latest = {}

    for row in rows:
        ticker = str(row.get("ticker", "")).upper()
        if ticker:
            latest[ticker] = row

    return latest


def thesis_icon(status):
    status = str(status or "").lower()

    if status == "intact":
        return "✅ Intact"
    if status == "strengthening":
        return "✅ Strengthening"
    if status == "weakening":
        return "⚠️ Weakening"
    if status == "needs_review":
        return "⚠️ Review"
    if status == "invalidated":
        return "❌ Invalidated"
    if status == "closed":
        return "— Closed"

    return "⚠️ Unknown"


def account_taxable_type(account_type):
    return account_type == "Cash / Non-registered"


def registered_note(account_type, account_group):
    if account_group == "Company Retirement":
        return "Company retirement; keep separate from stock account tax optimization."
    if account_type == "TFSA":
        return "Tax-free account; no normal capital gain/loss estimate."
    if account_type == "FHSA":
        return "FHSA; qualifying home withdrawal is tax-free."
    if account_type == "RRSP":
        return "RRSP; internal gains/losses not tracked as current capital gains."
    if account_type == "RESP":
        return "RESP; track separately."
    return "Review account treatment."


def tax_action_for_position(row, latest_thesis):
    account_type = row.get("account_type", "")
    account_group = row.get("account_group", "")
    ticker = str(row.get("ticker", "")).upper()

    pnl_cad = safe_float(row.get("unrealized_pnl_cad"))
    market_value_cad = safe_float(row.get("market_value_cad"))
    tax_on_gain = safe_float(row.get("estimated_tax_on_gain_cad"))
    loss_value = safe_float(row.get("estimated_loss_offset_value_cad"))

    thesis = latest_thesis.get(ticker, {})
    thesis_status = thesis.get("thesis_status", row.get("thesis_status", "needs_review"))
    thesis_state = thesis_icon(thesis_status)

    taxable = account_taxable_type(account_type)

    if not taxable:
        return {
            "taxable": False,
            "tax_status": "registered_or_separate",
            "tax_note": registered_note(account_type, account_group),
            "tax_action": "Performance / allocation review only",
            "thesis_state": thesis_state,
            "priority": "low"
        }

    if market_value_cad <= 0:
        return {
            "taxable": True,
            "tax_status": "missing_value",
            "tax_note": "Market value missing.",
            "tax_action": "Update current value before tax review",
            "thesis_state": thesis_state,
            "priority": "medium"
        }

    if pnl_cad > 0:
        if str(thesis_status).lower() in ["invalidated", "weakening"]:
            action = "Review trimming; taxable gain exists and thesis is weak."
            priority = "medium"
        else:
            action = "Do not sell only for tax; review thesis and portfolio need first."
            priority = "low"

        return {
            "taxable": True,
            "tax_status": "unrealized_gain",
            "tax_note": f"Estimated tax on gain: ${tax_on_gain:,.2f} CAD.",
            "tax_action": action,
            "thesis_state": thesis_state,
            "priority": priority
        }

    if pnl_cad < 0:
        if str(thesis_status).lower() in ["invalidated", "weakening", "needs_review"]:
            action = "Potential tax-loss harvest candidate; check superficial-loss risk first."
            priority = "high"
        else:
            action = "Loss exists, but thesis may still be intact; do not harvest blindly."
            priority = "medium"

        return {
            "taxable": True,
            "tax_status": "unrealized_loss",
            "tax_note": f"Estimated loss offset value: ${loss_value:,.2f} CAD.",
            "tax_action": action,
            "thesis_state": thesis_state,
            "priority": priority
        }

    return {
        "taxable": True,
        "tax_status": "flat",
        "tax_note": "No meaningful unrealized gain/loss.",
        "tax_action": "No tax action needed.",
        "thesis_state": thesis_state,
        "priority": "low"
    }


def superficial_loss_warning(position, all_positions):
    ticker = str(position.get("ticker", "")).upper()
    account_type = position.get("account_type", "")
    pnl_cad = safe_float(position.get("unrealized_pnl_cad"))

    if pnl_cad >= 0:
        return "—"

    matching_accounts = []

    for row in all_positions:
        if str(row.get("ticker", "")).upper() == ticker and row is not position:
            matching_accounts.append(f"{row.get('account_name')} ({row.get('account_type')})")

    if matching_accounts:
        return "⚠️ Same ticker exists in other account(s); review superficial-loss risk."

    if account_type == "Cash / Non-registered":
        return "⚠️ Check 30-day repurchase window before harvesting loss."

    return "—"


def analyze():
    account_packet = load_json(ACCOUNT_PORTFOLIO, {"positions": []})
    fx_packet = load_json(FX_RATES, {"rates": {}})
    fund_packet = load_json(MUTUAL_FUND_RESEARCH, {"funds": []})

    positions = account_packet.get("positions", [])
    latest_thesis = latest_thesis_by_ticker()

    stock_total_cad = 0.0
    retirement_total_cad = 0.0
    other_total_cad = 0.0

    taxable_gain_cad = 0.0
    taxable_loss_cad = 0.0
    estimated_tax_cad = 0.0
    estimated_loss_offset_cad = 0.0

    rows = []

    for position in positions:
        group = position.get("account_group", "Stock Account")
        value_cad = safe_float(position.get("market_value_cad"))
        pnl_cad = safe_float(position.get("unrealized_pnl_cad"))
        account_type = position.get("account_type", "")

        if group == "Company Retirement":
            retirement_total_cad += value_cad
        elif group == "Stock Account":
            stock_total_cad += value_cad
        else:
            other_total_cad += value_cad

        taxable = account_taxable_type(account_type)

        if taxable:
            if pnl_cad > 0:
                taxable_gain_cad += pnl_cad
                estimated_tax_cad += safe_float(position.get("estimated_tax_on_gain_cad"))
            elif pnl_cad < 0:
                taxable_loss_cad += abs(pnl_cad)
                estimated_loss_offset_cad += safe_float(position.get("estimated_loss_offset_value_cad"))

        tax_read = tax_action_for_position(position, latest_thesis)

        rows.append({
            "Account": position.get("account_name", ""),
            "Group": group,
            "Type": account_type,
            "Ticker": position.get("ticker", ""),
            "Acct Ccy": position.get("account_currency", ""),
            "Sec Ccy": position.get("security_currency", ""),
            "CAD Value": round(value_cad, 2),
            "CAD P&L": round(pnl_cad, 2),
            "Taxable": "✅" if taxable else "—",
            "Tax Status": tax_read.get("tax_status"),
            "Tax Note": tax_read.get("tax_note"),
            "Superficial Risk": superficial_loss_warning(position, positions),
            "Thesis": tax_read.get("thesis_state"),
            "Priority": tax_read.get("priority"),
            "Suggested Review": tax_read.get("tax_action")
        })

    overall_total_cad = stock_total_cad + retirement_total_cad + other_total_cad

    loss_candidates = [row for row in rows if row.get("Tax Status") == "unrealized_loss"]
    gain_positions = [row for row in rows if row.get("Tax Status") == "unrealized_gain"]
    high_priority = [row for row in rows if row.get("Priority") == "high"]

    blockers = []
    next_actions = []
    positives = []

    if not positions:
        blockers.append("No account positions are saved yet.")
        next_actions.append("Add positions in Account Portfolio / Tax.")
    else:
        positives.append(f"{len(positions)} account position(s) available for tax review.")

    if taxable_gain_cad > 0:
        positives.append(f"Taxable unrealized gains identified: ${taxable_gain_cad:,.2f} CAD.")

    if taxable_loss_cad > 0:
        positives.append(f"Taxable unrealized losses identified: ${taxable_loss_cad:,.2f} CAD.")
        next_actions.append("Review taxable loss candidates for possible offset opportunities.")

    if loss_candidates:
        next_actions.append("Check superficial-loss risk before any tax-loss harvesting.")

    if high_priority:
        next_actions.append("Review high-priority tax candidates first.")

    if retirement_total_cad > 0:
        positives.append(f"Company retirement balance tracked separately: ${retirement_total_cad:,.2f} CAD.")

    funds = fund_packet.get("funds", [])
    if funds:
        positives.append(f"{len(funds)} mutual fund/retirement option(s) saved for retirement review.")

    if not next_actions:
        next_actions.append("No urgent tax action. Continue tracking account balances, FX, thesis status, and realized trades.")

    if high_priority:
        overall = "red"
        headline = "Tax Advisor found high-priority review candidates."
    elif loss_candidates or gain_positions:
        overall = "yellow"
        headline = "Tax Advisor found taxable positions to review."
    elif positions:
        overall = "green"
        headline = "Tax Advisor has no urgent taxable action."
    else:
        overall = "data_missing"
        headline = "Tax Advisor needs account data."

    return {
        "timestamp": now_utc(),
        "overall": overall,
        "headline": headline,
        "base_currency": "CAD",
        "totals": {
            "stock_accounts_cad": round(stock_total_cad, 2),
            "company_retirement_cad": round(retirement_total_cad, 2),
            "other_cad": round(other_total_cad, 2),
            "overall_cad": round(overall_total_cad, 2),
            "taxable_unrealized_gains_cad": round(taxable_gain_cad, 2),
            "taxable_unrealized_losses_cad": round(taxable_loss_cad, 2),
            "estimated_tax_on_gains_cad": round(estimated_tax_cad, 2),
            "estimated_loss_offset_value_cad": round(estimated_loss_offset_cad, 2)
        },
        "counts": {
            "positions": len(positions),
            "taxable_gain_positions": len(gain_positions),
            "taxable_loss_candidates": len(loss_candidates),
            "high_priority": len(high_priority),
            "mutual_funds": len(funds)
        },
        "positives": positives,
        "blockers": blockers,
        "next_actions": next_actions[:8],
        "rows": rows,
        "fx_source": fx_packet.get("source_read", ""),
        "source_files": {
            "account_portfolio": str(ACCOUNT_PORTFOLIO),
            "fx_rates": str(FX_RATES),
            "mutual_fund_research": str(MUTUAL_FUND_RESEARCH)
        },
        "disclaimer": "Planning aid only. Confirm tax decisions with a qualified Canadian tax professional."
    }


def main():
    payload = analyze()

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Hermes Tax Advisor")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append(f"## {payload['headline']}")
    lines.append("")
    lines.append(f"- Overall: {payload['overall']}")
    lines.append(f"- Base currency: CAD")
    lines.append("")
    lines.append("## Totals")
    for key, value in payload["totals"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Next Actions")
    for item in payload["next_actions"]:
        lines.append(f"- {item}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "overall": payload["overall"],
        "headline": payload["headline"],
        "positions": payload["counts"]["positions"],
        "taxable_loss_candidates": payload["counts"]["taxable_loss_candidates"],
        "json": str(OUT_JSON),
        "report": str(OUT_MD)
    }, indent=2))


if __name__ == "__main__":
    main()
