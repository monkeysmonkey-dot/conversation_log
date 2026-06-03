import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = Path(__file__).resolve().parents[1]

MUTUAL_FUND_RESEARCH = BASE / "data" / "mutual_fund_research.json"
MUTUAL_FUND_ANALYSIS = BASE / "features" / "latest_mutual_fund_analysis.json"

OUT_JSON = BASE / "features" / "latest_mutual_fund_review_schedule.json"
OUT_MD = BASE / "reports" / "daily" / "latest_mutual_fund_review_schedule.md"


def now_utc():
    return datetime.now(timezone.utc)


def now_iso():
    return now_utc().isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_dt(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def days_since(value):
    dt = parse_dt(value)

    if not dt:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return (now_utc() - dt).days


def review_status(days, threshold):
    if days is None:
        return "due"

    if days >= threshold:
        return "due"

    if days >= threshold * 0.75:
        return "soon"

    return "current"


def status_icon(status):
    if status == "current":
        return "✅"
    if status == "soon":
        return "⚠️"
    return "🔴"


def fund_review_row(fund):
    fund_key = fund.get("fund_key") or fund.get("fund_name") or fund.get("fund_code") or "UNKNOWN"
    updated_at = fund.get("updated_at", "")
    age_days = days_since(updated_at)

    monthly_status = review_status(age_days, 30)
    quarterly_status = review_status(age_days, 90)

    factsheet_lines = int(fund.get("factsheet_line_count", 0) or 0)
    mer = float(fund.get("mer", 0) or 0)
    current_value = float(fund.get("current_value", 0) or 0)
    cash_yield = float(fund.get("cash_yield", 0) or 0)

    blockers = []
    next_actions = []

    if factsheet_lines <= 0:
        blockers.append("Factsheet/holdings data missing")
        next_actions.append("Paste latest fund factsheet or holdings.")

    if mer <= 0:
        blockers.append("MER/fee missing")
        next_actions.append("Enter MER/fee.")

    if current_value <= 0:
        blockers.append("Current value missing")
        next_actions.append("Update current invested value.")

    if cash_yield <= 0:
        next_actions.append("Update cash/money market yield for comparison.")

    if monthly_status == "due":
        next_actions.append("Run monthly quick review.")
    elif monthly_status == "soon":
        next_actions.append("Monthly review coming due soon.")

    if quarterly_status == "due":
        next_actions.append("Run quarterly deep review.")
    elif quarterly_status == "soon":
        next_actions.append("Quarterly deep review coming due soon.")

    if not next_actions:
        next_actions.append("Keep in normal monitoring cycle.")

    return {
        "fund_key": fund_key,
        "account": fund.get("account_name", ""),
        "account_type": fund.get("account_type", ""),
        "fund": fund.get("fund_name") or fund.get("fund_code") or fund_key,
        "last_updated": updated_at,
        "age_days": age_days,
        "monthly_status": monthly_status,
        "quarterly_status": quarterly_status,
        "factsheet_ready": factsheet_lines > 0,
        "fee_ready": mer > 0,
        "value_ready": current_value > 0,
        "cash_compare_ready": cash_yield > 0,
        "blockers": blockers,
        "next_actions": next_actions[:5]
    }


def main():
    research = load_json(MUTUAL_FUND_RESEARCH, {"funds": []})
    analysis = load_json(MUTUAL_FUND_ANALYSIS, {})

    funds = research.get("funds", [])
    rows = [fund_review_row(fund) for fund in funds]

    monthly_due = [x for x in rows if x.get("monthly_status") == "due"]
    quarterly_due = [x for x in rows if x.get("quarterly_status") == "due"]
    soon = [x for x in rows if x.get("monthly_status") == "soon" or x.get("quarterly_status") == "soon"]

    if not funds:
        overall = "data_missing"
        headline = "No retirement mutual fund data saved yet."
        next_actions = ["Paste at least one available mutual fund or retirement account option."]
    elif quarterly_due:
        overall = "red"
        headline = "Quarterly mutual fund deep review is due."
        next_actions = ["Run quarterly deep review for due funds."]
    elif monthly_due:
        overall = "yellow"
        headline = "Monthly mutual fund quick review is due."
        next_actions = ["Update values, fees, cash yield, and factsheet data for due funds."]
    elif soon:
        overall = "yellow"
        headline = "Some mutual fund reviews are coming due soon."
        next_actions = ["Prepare monthly or quarterly review updates."]
    else:
        overall = "green"
        headline = "Mutual fund review schedule is current."
        next_actions = ["Continue normal monthly and quarterly review cycle."]

    for row in rows:
        for action in row.get("next_actions", []):
            if action not in next_actions:
                next_actions.append(action)

    payload = {
        "timestamp": now_iso(),
        "overall": overall,
        "headline": headline,
        "fund_count": len(funds),
        "monthly_due_count": len(monthly_due),
        "quarterly_due_count": len(quarterly_due),
        "soon_count": len(soon),
        "rows": rows,
        "next_actions": next_actions[:8],
        "analysis_headline": analysis.get("headline", ""),
        "source_files": {
            "mutual_fund_research": str(MUTUAL_FUND_RESEARCH),
            "mutual_fund_analysis": str(MUTUAL_FUND_ANALYSIS)
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Mutual Fund Review Schedule")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append(f"## {headline}")
    lines.append("")
    lines.append(f"- Overall: {overall}")
    lines.append(f"- Funds tracked: {len(funds)}")
    lines.append(f"- Monthly due: {len(monthly_due)}")
    lines.append(f"- Quarterly due: {len(quarterly_due)}")
    lines.append(f"- Coming due soon: {len(soon)}")
    lines.append("")
    lines.append("## Next Actions")
    for action in payload["next_actions"]:
        lines.append(f"- {action}")
    lines.append("")
    lines.append("## Fund Review Rows")
    for row in rows:
        lines.append("")
        lines.append(f"### {row.get('fund')}")
        lines.append(f"- Account: {row.get('account')}")
        lines.append(f"- Monthly: {row.get('monthly_status')}")
        lines.append(f"- Quarterly: {row.get('quarterly_status')}")
        lines.append(f"- Age days: {row.get('age_days')}")
        if row.get("blockers"):
            lines.append("- Blockers: " + "; ".join(row.get("blockers", [])))

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "overall": overall,
        "headline": headline,
        "fund_count": len(funds),
        "monthly_due": len(monthly_due),
        "quarterly_due": len(quarterly_due),
        "json": str(OUT_JSON),
        "report": str(OUT_MD)
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
