ï»¿import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

MUTUAL_FUND_RESEARCH = BASE / "data" / "mutual_fund_research.json"
ACCOUNT_PORTFOLIOS = BASE / "data" / "account_portfolios.json"

OUT_JSON = BASE / "features" / "latest_mutual_fund_analysis.json"
OUT_MD = BASE / "reports" / "daily" / "latest_mutual_fund_analysis.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_float(value):
    try:
        if value in [None, ""]:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def fee_rating(mer):
    mer = safe_float(mer)

    if mer <= 0:
        return "âš ï¸ fee missing", "Add MER/fee before ranking this fund."
    if mer <= 0.35:
        return "âœ… low fee", "Fee drag appears low."
    if mer <= 0.85:
        return "âš ï¸ moderate fee", "Fee is acceptable only if performance/holdings justify it."
    return "âŒ high fee", "High fee drag. Fund needs strong justification versus index/cash alternatives."


def performance_read(perf):
    one = safe_float(perf.get("1y"))
    three = safe_float(perf.get("3y"))
    five = safe_float(perf.get("5y"))
    ten = safe_float(perf.get("10y"))

    available = [x for x in [one, three, five, ten] if x != 0]

    if not available:
        return "âš ï¸ performance missing", "Add 1Y/3Y/5Y/10Y returns before comparing."

    if five > 0 and ten > 0 and one > 0:
        return "âœ… positive history", "Short and long-term performance are positive."

    if one < 0 and five > 0:
        return "âš ï¸ recent weakness", "Longer-term record exists, but recent performance weakened."

    if five < 0 or ten < 0:
        return "âŒ weak long-term", "Long-term performance is weak or negative."

    return "âš ï¸ mixed history", "Performance is mixed. Compare against benchmark and cash option."


def cash_compare(perf, cash_yield):
    cash = safe_float(cash_yield)
    one = safe_float(perf.get("1y"))
    three = safe_float(perf.get("3y"))

    if cash <= 0:
import os
API_KEY = os.getenv("API_KEY")

    if one <= cash and three <= cash:
        return "âŒ cash competitive", "Fund has not clearly beaten cash on entered 1Y/3Y numbers."

    if one > cash or three > cash:
        return "âœ… beats cash", "Fund performance is above the cash option on at least one entered period."

    return "âš ï¸ compare manually", "Cash comparison needs review."


def research_read(fund):
    line_count = int(fund.get("factsheet_line_count", 0) or 0)
    allocation_lines = fund.get("possible_holding_or_allocation_lines", [])

    if line_count <= 0:
        return "âŒ factsheet missing", "Paste holdings/factsheet data for deeper analysis."

    if len(allocation_lines) >= 5:
        return "âœ… holdings available", "Holdings/allocation clues are available for agent analysis."

    return "âš ï¸ partial factsheet", "Some factsheet text exists, but holdings/allocation detail may be incomplete."


def suitability_read(fund):
    account_type = fund.get("account_type", "")
    style = fund.get("fund_style", "")
    risk = fund.get("risk_rating", "")
    review = fund.get("review_status", "")

    if review == "avoid":
        return "âŒ avoid", "Marked as avoid by user/system review."

    if style == "money market":
        return "âš ï¸ cash option", "Cash-like option. Useful for defense, but compare yield versus inflation/opportunity cost."

    if account_type in ["Company Retirement", "Group RRSP", "Defined Contribution Pension", "RRSP"]:
        if risk in ["high", "very high"]:
            return "âš ï¸ retirement risk", "High-risk fund inside retirement account; confirm time horizon and diversification."
        return "âœ… retirement eligible", "Fund can be considered within retirement allocation review."

    if account_type in ["TFSA", "FHSA"]:
        return "âœ… registered growth account", "Track performance and allocation; normal capital gain/loss tax estimates are not required."

    return "âš ï¸ review fit", "Account/fund fit needs review."


def analyze_fund(fund):
    mer = safe_float(fund.get("mer"))
    perf = fund.get("performance", {})
    cash_yield = safe_float(fund.get("cash_yield"))

    fee_status, fee_read = fee_rating(mer)
    perf_status, perf_text = performance_read(perf)
    cash_status, cash_text = cash_compare(perf, cash_yield)
    research_status, research_text = research_read(fund)
    suit_status, suit_text = suitability_read(fund)

    blockers = []
    positives = []
    next_actions = []

    for status, text in [
        (fee_status, fee_read),
        (perf_status, perf_text),
        (cash_status, cash_text),
        (research_status, research_text),
        (suit_status, suit_text),
    ]:
        if status.startswith("âœ…"):
            positives.append(text)
        elif status.startswith("âŒ"):
            blockers.append(text)
            next_actions.append(text)
        else:
            next_actions.append(text)

    if not next_actions:
        next_actions.append("Keep fund in normal review cycle.")

    score = 0
    for status in [fee_status, perf_status, cash_status, research_status, suit_status]:
        if status.startswith("âœ…"):
            score += 2
        elif status.startswith("âš ï¸"):
            score += 1
        else:
            score -= 1

    if score >= 7:
        overall = "âœ… strong candidate"
    elif score >= 4:
        overall = "âš ï¸ review candidate"
    else:
        overall = "âŒ weak / incomplete"

    return {
        "fund_key": fund.get("fund_key"),
        "account": fund.get("account_name"),
        "account_type": fund.get("account_type"),
        "fund": fund.get("fund_name") or fund.get("fund_code"),
        "style": fund.get("fund_style"),
        "risk": fund.get("risk_rating"),
        "current_value": safe_float(fund.get("current_value")),
        "allocation_pct": safe_float(fund.get("contribution_pct")),
        "mer": mer,
        "fee_status": fee_status,
        "performance_status": perf_status,
        "cash_status": cash_status,
        "research_status": research_status,
        "suitability_status": suit_status,
        "overall": overall,
        "positives": positives,
        "blockers": blockers,
        "next_actions": next_actions[:5],
        "thesis": fund.get("thesis_summary", ""),
        "updated_at": fund.get("updated_at", "")
    }


def main():
    fund_packet = load_json(MUTUAL_FUND_RESEARCH, {"funds": []})
    account_packet = load_json(ACCOUNT_PORTFOLIOS, {"positions": []})

    funds = fund_packet.get("funds", [])
    analyses = [analyze_fund(fund) for fund in funds]

    total_value = sum(safe_float(item.get("current_value")) for item in analyses)

    account_values = {}
    for item in analyses:
        account = item.get("account") or "Unknown"
        account_values.setdefault(account, 0.0)
        account_values[account] += safe_float(item.get("current_value"))

    if not funds:
        headline = "No mutual fund research saved yet."
        overall = "data_missing"
        next_actions = ["Paste at least one mutual fund factsheet or available fund option."]
    else:
        weak = [x for x in analyses if str(x.get("overall", "")).startswith("âŒ")]
        review = [x for x in analyses if str(x.get("overall", "")).startswith("âš ï¸")]

        if weak:
            headline = "Some retirement fund options need attention."
            overall = "red"
        elif review:
            headline = "Retirement fund options are partially reviewed."
            overall = "yellow"
        else:
            headline = "Retirement fund options look review-ready."
            overall = "green"

        next_actions = []
        for item in analyses:
            for action in item.get("next_actions", []):
                if action not in next_actions:
                    next_actions.append(action)

        if not next_actions:
            next_actions = ["Continue monitoring fund performance, fees, holdings, and allocation."]

    payload = {
        "timestamp": now_utc(),
        "overall": overall,
        "headline": headline,
        "fund_count": len(funds),
        "total_value": total_value,
        "account_values": account_values,
        "analyses": analyses,
        "next_actions": next_actions[:8],
        "source_files": {
            "mutual_fund_research": str(MUTUAL_FUND_RESEARCH),
            "account_portfolios": str(ACCOUNT_PORTFOLIOS)
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Mutual Fund / Retirement Analysis")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append(f"## {headline}")
    lines.append("")
    lines.append(f"- Overall: {overall}")
    lines.append(f"- Fund count: {len(funds)}")
    lines.append(f"- Total tracked value: {total_value}")
    lines.append("")
    lines.append("## Next Actions")
    for action in payload["next_actions"]:
        lines.append(f"- {action}")
    lines.append("")
    lines.append("## Fund Reads")
    for item in analyses:
        lines.append("")
        lines.append(f"### {item.get('fund')}")
        lines.append(f"- Overall: {item.get('overall')}")
        lines.append(f"- Fee: {item.get('fee_status')}")
        lines.append(f"- Performance: {item.get('performance_status')}")
        lines.append(f"- Cash compare: {item.get('cash_status')}")
        lines.append(f"- Research: {item.get('research_status')}")
        lines.append(f"- Suitability: {item.get('suitability_status')}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "overall": overall,
        "headline": headline,
        "fund_count": len(funds),
        "total_value": total_value,
        "json": str(OUT_JSON),
        "report": str(OUT_MD)
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()