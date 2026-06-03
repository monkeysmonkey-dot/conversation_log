import json
import calendar
from pathlib import Path
from datetime import datetime, timezone, timedelta, date

BASE = Path(__file__).resolve().parents[1]

CONFIG_PATH = BASE / "config" / "market_mechanics_calendar.json"
LATEST_JSON = BASE / "features" / "latest_market_mechanics.json"
REPORT_MD = BASE / "reports" / "macro" / "latest_market_mechanics_report.md"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def today_date():
    return datetime.now().date()

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def third_friday(year, month):
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    fridays = [
        d for d in cal.itermonthdates(year, month)
        if d.month == month and d.weekday() == 4
    ]
    return fridays[2] if len(fridays) >= 3 else None

def last_business_days(year, month, n=3):
    last_day = calendar.monthrange(year, month)[1]
    days = []
    d = date(year, month, last_day)

    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)

    return sorted(days)

def days_until(d):
    return (d - today_date()).days

def within_window(d, before=7, after=1):
    diff = days_until(d)
    return -after <= diff <= before

def classify_pressure(days_to_event, event_type):
    if days_to_event is None:
        return "unknown"

    if -1 <= days_to_event <= 2:
        return "high"

    if 3 <= days_to_event <= 7:
        return "medium"

    if 8 <= days_to_event <= 21:
        return "low_to_medium"

    return "background"

def build_options_expiry_events(cfg):
    now = today_date()
    events = []

    for offset_month in range(0, 4):
        year = now.year
        month = now.month + offset_month

        while month > 12:
            month -= 12
            year += 1

        exp = third_friday(year, month)
        if not exp:
            continue

        diff = days_until(exp)
        if -2 <= diff <= 30:
            is_triple = month in cfg.get("event_types", {}).get("triple_witching", {}).get("months", [])

            events.append({
                "event_type": "triple_witching" if is_triple else "monthly_options_expiry",
                "label": "Triple Witching" if is_triple else "Monthly Options Expiry",
                "date": exp.isoformat(),
                "days_until": diff,
                "mechanical_pressure": classify_pressure(diff, "options_expiry"),
                "expected_effect": "Higher volume, dealer hedging, pinning risk, and short-term volatility are possible.",
                "affected_assets": ["SPY", "QQQ", "IWM", "high open-interest mega caps"],
                "interpretation": "Do not overread expiration-window price action as fundamental unless it persists after expiry."
            })

    return events

def build_month_quarter_end_events(cfg):
    now = today_date()
    events = []

    for offset_month in range(0, 3):
        year = now.year
        month = now.month + offset_month

        while month > 12:
            month -= 12
            year += 1

        business_days = last_business_days(year, month, 3)

        for d in business_days:
            diff = days_until(d)
            if -1 <= diff <= 10:
                is_quarter_end = month in [3, 6, 9, 12]

                events.append({
                    "event_type": "quarter_end_rebalance" if is_quarter_end else "month_end_rebalance",
                    "label": "Quarter-End Rebalance" if is_quarter_end else "Month-End Rebalance",
                    "date": d.isoformat(),
                    "days_until": diff,
                    "mechanical_pressure": classify_pressure(diff, "rebalance"),
                    "expected_effect": "Portfolio and index rebalancing can distort flows near the close.",
                    "affected_assets": ["SPY", "QQQ", "sector ETFs", "large index constituents"],
                    "interpretation": "Short-term moves near month/quarter end may reflect rebalancing rather than thesis change."
                })

    return events

def build_tax_events(cfg):
    now = today_date()
    events = []
    tax_cfg = cfg.get("event_types", {}).get("tax_liquidity", {})

    for win in tax_cfg.get("windows", []):
        month = win.get("month")
        start = win.get("day_start")
        end = win.get("day_end")
        label = win.get("label")

        if not month or not start or not end:
            continue

        start_d = date(now.year, month, start)
        end_d = date(now.year, month, end)

        if end_d < now:
            start_d = date(now.year + 1, month, start)
            end_d = date(now.year + 1, month, end)

        diff = days_until(start_d)

        if -5 <= diff <= 45 or start_d <= now <= end_d:
            events.append({
                "event_type": "tax_liquidity",
                "label": label,
                "date": f"{start_d.isoformat()} to {end_d.isoformat()}",
                "days_until": diff,
                "mechanical_pressure": "medium" if start_d <= now <= end_d else classify_pressure(diff, "tax_liquidity"),
                "expected_effect": "Liquidity raising, tax payments, or tax-loss harvesting can create non-fundamental selling pressure.",
                "affected_assets": ["prior winners", "prior losers", "high retail ownership names", "illiquid growth stocks"],
                "interpretation": "Selling pressure during tax windows may be liquidity-driven; confirmation after the window matters."
            })

    return events

def build_seasonality_events(cfg):
    now = today_date()
    events = []
    seasonal_cfg = cfg.get("event_types", {}).get("seasonality", {})

    for win in seasonal_cfg.get("windows", []):
        m1 = win.get("month_start")
        m2 = win.get("month_end")
        label = win.get("label")
        read = win.get("read")

        if not m1 or not m2:
            continue

        if m1 <= now.month <= m2:
            events.append({
                "event_type": "seasonality",
                "label": label,
                "date": f"month {m1} to {m2}",
                "days_until": 0,
                "mechanical_pressure": "background",
                "expected_effect": read,
                "affected_assets": ["broad market", "growth stocks", "seasonally sensitive groups"],
                "interpretation": "Seasonality is context, not a deterministic signal. Use it to adjust confidence and false-breakout risk."
            })

    return events

def build_manual_events(cfg):
    events = []
    now = today_date()

    for ev in cfg.get("manual_events", []):
        event_type = ev.get("event_type")
        label = ev.get("label", event_type)
        ticker = ev.get("ticker", "")
        ipo_date = ev.get("ipo_date", "")

        if not ticker and not ipo_date:
            continue

        event = {
            "event_type": event_type,
            "label": label,
            "ticker": ticker,
            "company": ev.get("company", ""),
            "ipo_date": ipo_date,
            "mechanical_pressure": "medium",
            "expected_effect": "Manual event requires review. Estimate passive inclusion, ETF inflow, lock-up risk, and collateral selling pressure.",
            "affected_assets": ["QQQ", "mega-cap index weights", "related thematic ETFs", "sector peers"],
            "interpretation": "Treat this as a watch item until dates, float, market cap, and index eligibility are verified.",
            "notes": ev.get("notes", "")
        }

        if ipo_date:
            try:
                ipo_d = datetime.fromisoformat(ipo_date).date()
                event["days_since_ipo"] = (now - ipo_d).days
                event["ipo_plus_7_trading_day_proxy"] = (ipo_d + timedelta(days=10)).isoformat()
                event["ipo_plus_15_trading_day_proxy"] = (ipo_d + timedelta(days=21)).isoformat()
                event["lockup_expiration_proxy"] = (ipo_d + timedelta(days=180)).isoformat()
            except Exception:
                pass

        events.append(event)

    return events

def build_mechanics_summary(events):
    active = [e for e in events if e.get("days_until") is not None and -1 <= e.get("days_until", 999) <= 7]
    high = [e for e in events if e.get("mechanical_pressure") == "high"]
    medium = [e for e in events if e.get("mechanical_pressure") == "medium"]

    if high:
        pressure = "high"
    elif medium or active:
        pressure = "medium"
    elif events:
        pressure = "low_to_background"
    else:
        pressure = "none_detected"

    top_events = sorted(
        events,
        key=lambda x: abs(x.get("days_until", 999)) if x.get("days_until") is not None else 999
    )[:5]

    interpretation = []

    if pressure == "high":
        interpretation.append("Mechanical flow risk is elevated. Avoid overinterpreting short-term moves as fundamental until post-event confirmation.")
    elif pressure == "medium":
        interpretation.append("Some mechanical pressure windows are active or near. Treat unusual moves with event-calendar context.")
    elif pressure == "low_to_background":
        interpretation.append("Mechanical events exist but appear mostly background. Use as context, not primary signal.")
    else:
        interpretation.append("No major mechanical market event detected from configured calendar.")

    if any(e.get("event_type") in ["triple_witching", "monthly_options_expiry"] for e in top_events):
        interpretation.append("Options expiry can create pinning, dealer hedging, and late-day volatility.")

    if any("rebalance" in e.get("event_type", "") for e in top_events):
        interpretation.append("Rebalance windows can create non-fundamental flows in index-heavy names.")

    if any(e.get("event_type") == "tax_liquidity" for e in top_events):
        interpretation.append("Tax windows can create liquidity-driven selling pressure or post-window relief.")

    return {
        "mechanical_pressure": pressure,
        "top_events": top_events,
        "interpretation": " ".join(interpretation)
    }

def prospect_exposure_template():
    return {
        "mega_cap_index_weight_risk": "check_if_high_weight_constituent",
        "options_expiry_sensitivity": "check_open_interest_and_liquidity",
        "tax_liquidity_sensitivity": "check_prior_winner_or_loser_status",
        "seasonality_context": "background",
        "mechanical_vs_fundamental_note": "If price move occurs during event window, confirm after event before treating as thesis change."
    }

def main():
    cfg = load_json(CONFIG_PATH, {})
    events = []

    events.extend(build_options_expiry_events(cfg))
    events.extend(build_month_quarter_end_events(cfg))
    events.extend(build_tax_events(cfg))
    events.extend(build_seasonality_events(cfg))
    events.extend(build_manual_events(cfg))

    summary = build_mechanics_summary(events)

    payload = {
        "timestamp": utc_now(),
        "summary": summary,
        "events": events,
        "prospect_exposure_template": prospect_exposure_template(),
        "advisory_note": "This layer identifies public, rules-based market mechanics and calendar risk. It is not a trade execution instruction."
    }

    save_json(LATEST_JSON, payload)

    lines = []
    lines.append("# Market Mechanics / Structural Flow Report")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Mechanical pressure: {summary.get('mechanical_pressure')}")
    lines.append(f"- Interpretation: {summary.get('interpretation')}")
    lines.append("")
    lines.append("## Top Mechanical Events")
    lines.append("")

    for event in summary.get("top_events", []):
        lines.append(f"### {event.get('label')}")
        lines.append(f"- Type: {event.get('event_type')}")
        lines.append(f"- Date: {event.get('date')}")
        lines.append(f"- Days until: {event.get('days_until')}")
        lines.append(f"- Mechanical pressure: {event.get('mechanical_pressure')}")
        lines.append(f"- Expected effect: {event.get('expected_effect')}")
        lines.append(f"- Affected assets: {', '.join(event.get('affected_assets', []))}")
        lines.append(f"- Interpretation: {event.get('interpretation')}")
        lines.append("")

    if not summary.get("top_events"):
        lines.append("- No upcoming configured mechanical events detected.")
        lines.append("")

    lines.append("## Event Framework")
    lines.append("")
    lines.append("- Mega IPO / index inclusion: model possible passive inclusion, sell-to-fund pressure, thematic ETF inflows, and lock-up risk.")
    lines.append("- ETF/index rebalance: model forced additions, deletions, and weight changes.")
    lines.append("- Options expiry: model pinning, dealer hedging, and temporary volatility.")
    lines.append("- Tax/seasonality: model liquidity-driven selling or participation changes.")
    lines.append("")
    lines.append("## Advisory Note")
    lines.append("")
    lines.append(payload["advisory_note"])

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "json": str(LATEST_JSON),
        "report": str(REPORT_MD),
        "mechanical_pressure": summary.get("mechanical_pressure"),
        "event_count": len(events)
    }, indent=2))

if __name__ == "__main__":
    main()
