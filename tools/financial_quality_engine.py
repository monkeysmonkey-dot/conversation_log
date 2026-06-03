import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
LATEST = BASE / "features" / "latest_candidates.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def safe_float(x, default=None):
    try:
        if x is None:
            return default
        s = str(x).replace("%", "").replace(",", "").strip()
        if s in ["", "-", "None", "none", "null"]:
            return default
        return float(s)
    except Exception:
        return default

def classify_cash_liquidity(f):
    cash_sh = safe_float(f.get("Cash/sh"))
    quick = safe_float(f.get("Quick Ratio"))
    current = safe_float(f.get("Current Ratio"))

    notes = []

    if cash_sh is not None:
        notes.append(f"cash/share {cash_sh}")

    if quick is not None:
        notes.append(f"quick ratio {quick}")

    if current is not None:
        notes.append(f"current ratio {current}")

    if quick is not None and quick < 1:
        label = "cash_constrained_or_liquidity_sensitive"
        read = "Quick ratio below 1.0 suggests liquidity is not strong."
    elif current is not None and current < 1:
        label = "cash_constrained_or_liquidity_sensitive"
        read = "Current ratio below 1.0 suggests near-term liquidity pressure."
    elif cash_sh is not None and cash_sh > 10:
        label = "cash_rich"
        read = "Cash per share appears strong."
    else:
        label = "balanced_or_unknown"
        read = "Liquidity profile is not clearly stressed from available fields."

    return label, read, notes

def classify_debt(f):
    debt_eq = safe_float(f.get("Debt/Eq"))
    lt_debt_eq = safe_float(f.get("LT Debt/Eq"))

    notes = []

    if debt_eq is not None:
        notes.append(f"Debt/Eq {debt_eq}")

    if lt_debt_eq is not None:
        notes.append(f"LT Debt/Eq {lt_debt_eq}")

    if debt_eq is not None and debt_eq >= 3:
        label = "high_leverage"
        read = "Debt/equity is high, increasing rate sensitivity and balance-sheet risk."
    elif debt_eq is not None and debt_eq >= 1:
        label = "moderate_leverage"
        read = "Debt/equity is meaningful but not extreme."
    elif debt_eq is not None:
        label = "low_leverage"
        read = "Debt/equity appears manageable."
    else:
        label = "unknown"
        read = "Debt profile is not available."

    return label, read, notes

def classify_profitability(f):
    income = safe_float(f.get("Income"))
    gross = safe_float(f.get("Gross Margin"))
    op = safe_float(f.get("Oper. Margin"))
    profit = safe_float(f.get("Profit Margin"))
    roa = safe_float(f.get("ROA"))
    roe = safe_float(f.get("ROE"))
    roic = safe_float(f.get("ROIC"))

    notes = []

    for label, val in [
        ("Income", income),
        ("Gross Margin", gross),
        ("Operating Margin", op),
        ("Profit Margin", profit),
        ("ROA", roa),
        ("ROE", roe),
        ("ROIC", roic)
    ]:
        if val is not None:
            notes.append(f"{label} {val}")

    if profit is not None and profit < 0:
        label = "unprofitable"
        read = "Profit margin is negative, so growth is not yet translating into bottom-line profitability."
    elif op is not None and op < 0:
        label = "operating_losses"
        read = "Operating margin is negative, indicating core operations are not yet profitable."
    elif profit is not None and profit > 15:
        label = "highly_profitable"
        read = "Profitability appears strong."
    elif profit is not None and profit > 0:
        label = "profitable"
        read = "Company is profitable but quality depends on margins and returns."
    else:
        label = "unknown"
        read = "Profitability profile is incomplete."

    return label, read, notes

def classify_growth(f):
    sales_yoy = safe_float(f.get("Sales Y/Y TTM"))
    sales_qoq = safe_float(f.get("Sales Q/Q"))
    sales_3y = safe_float(f.get("Sales past 3/5Y"))
    eps_yoy = safe_float(f.get("EPS Y/Y TTM"))
    eps_qoq = safe_float(f.get("EPS Q/Q"))
    eps_next_y = safe_float(f.get("EPS next Y"))

    notes = []

    for label, val in [
        ("Sales Y/Y TTM", sales_yoy),
        ("Sales Q/Q", sales_qoq),
        ("EPS Y/Y TTM", eps_yoy),
        ("EPS Q/Q", eps_qoq),
        ("EPS next Y", eps_next_y)
    ]:
        if val is not None:
            notes.append(f"{label} {val}")

    if sales_yoy is not None and sales_yoy > 25:
        if eps_yoy is not None and eps_yoy < 0:
            label = "high_growth_but_earnings_not_following"
            read = "Sales growth is strong, but earnings are not improving yet."
        else:
            label = "high_growth"
            read = "Sales growth is strong."
    elif sales_yoy is not None and sales_yoy > 5:
        label = "moderate_growth"
        read = "Sales growth is positive but not explosive."
    elif sales_yoy is not None and sales_yoy < 0:
        label = "contracting"
        read = "Sales are declining."
    else:
        label = "unknown"
        read = "Growth profile is incomplete."

    return label, read, notes

def classify_valuation(f):
    pe = safe_float(f.get("P/E"))
    fpe = safe_float(f.get("Forward P/E"))
    ps = safe_float(f.get("P/S"))
    pb = safe_float(f.get("P/B"))
    pfcf = safe_float(f.get("P/FCF"))
    ev_sales = safe_float(f.get("EV/Sales"))
    ev_ebitda = safe_float(f.get("EV/EBITDA"))

    notes = []

    for label, val in [
        ("P/E", pe),
        ("Forward P/E", fpe),
        ("P/S", ps),
        ("P/B", pb),
        ("P/FCF", pfcf),
        ("EV/Sales", ev_sales),
        ("EV/EBITDA", ev_ebitda)
    ]:
        if val is not None:
            notes.append(f"{label} {val}")

    if pe is None and fpe is None and ps is not None and ps > 5:
        label = "expensive_sales_multiple_with_no_earnings"
        read = "Valuation appears demanding because sales multiple is high while earnings multiples are unavailable or not meaningful."
    elif ps is not None and ps > 10:
        label = "very_expensive"
        read = "Sales multiple is very high."
    elif pe is not None and pe > 40:
        label = "expensive"
        read = "P/E is high and requires strong growth justification."
    elif pe is not None and pe > 0 and pe < 15:
        label = "cheap_or_value"
        read = "P/E appears low, but quality and cyclicality must be checked."
    else:
        label = "unknown_or_mixed"
        read = "Valuation read is mixed or incomplete."

    return label, read, notes

def classify_market_behavior(f, candidate):
    qt = candidate.get("questrade_market", {})
    qt_behavior = qt.get("market_behavior", {}) if isinstance(qt, dict) else {}

    if qt_behavior and not f:
        rel_vol = safe_float(qt_behavior.get("relative_volume"))
        read = qt_behavior.get("market_behavior_read", "mixed_or_unconfirmed")
        notes = [
            f"Questrade relative volume {rel_vol}",
            f"Questrade 1d change {qt_behavior.get('change_1d')}",
            f"Questrade 5d change {qt_behavior.get('change_5d')}",
            f"Questrade 20d change {qt_behavior.get('change_20d')}",
            f"Price vs SMA20 {qt_behavior.get('price_vs_sma20')}",
            f"Price vs SMA50 {qt_behavior.get('price_vs_sma50')}"
        ]

        return read, "Market behavior is based on Questrade quote/candle data: " + str(read), notes

    perf_week = safe_float(f.get("Perf Week"))
    perf_month = safe_float(f.get("Perf Month"))
    perf_q = safe_float(f.get("Perf Quarter"))
    perf_ytd = safe_float(f.get("Perf YTD"))
    perf_year = safe_float(f.get("Perf Year"))
    rel_vol = safe_float(f.get("Rel Volume"))
    short_float = safe_float(f.get("Short Float"))
    inst_trans = safe_float(f.get("Inst Trans"))
    insider_trans = safe_float(f.get("Insider Trans"))
    rsi = safe_float(f.get("RSI (14)"))

    trend = safe_float(candidate.get("trend_score"), 0)
    rs = safe_float(candidate.get("relative_strength_vs_spy"), 0)

    notes = []

    for label, val in [
        ("Perf Week", perf_week),
        ("Perf Month", perf_month),
        ("Perf Quarter", perf_q),
        ("Perf YTD", perf_ytd),
        ("Perf Year", perf_year),
        ("Rel Volume", rel_vol),
        ("Short Float", short_float),
        ("Inst Trans", inst_trans),
        ("Insider Trans", insider_trans),
        ("RSI", rsi)
    ]:
        if val is not None:
            notes.append(f"{label} {val}")

    if perf_month is not None and perf_month < -15 and perf_q is not None and perf_q < -25:
        if perf_week is not None and perf_week > 0:
            label = "bounce_after_heavy_selloff"
            read = "Recent bounce is occurring after a severe drawdown; could be dip buying or short-term relief rally."
        else:
            label = "persistent_selloff"
            read = "Price behavior looks like sustained selling pressure."
    elif trend >= 10 and rs > 0:
        label = "leadership_momentum"
        read = "Technical behavior suggests leadership momentum."
    else:
        label = "mixed"
        read = "Market behavior is mixed."

    if inst_trans is not None and inst_trans > 0:
        read += " Institutional transaction trend is positive."
    elif inst_trans is not None and inst_trans < 0:
        read += " Institutional transaction trend is negative."

    if insider_trans is not None and insider_trans < 0:
        read += " Insider transaction trend is negative."

    return label, read, notes

def classify_rate_sensitivity(debt_label, profitability_label, valuation_label):
    high = False
    reasons = []

    if debt_label in ["high_leverage", "moderate_leverage"]:
        high = True
        reasons.append("leverage")

    if profitability_label in ["unprofitable", "operating_losses"]:
        high = True
        reasons.append("negative profitability")

    if valuation_label in ["expensive_sales_multiple_with_no_earnings", "very_expensive", "expensive"]:
        high = True
        reasons.append("valuation sensitivity")

    if high:
        return "high", f"Fed-rate sensitivity is elevated due to {', '.join(reasons)}."
    return "medium_or_low", "Fed-rate sensitivity is not clearly extreme from available fields."

def build_financial_quality(candidate):
    f = candidate.get("fundamentals", {}) or candidate.get("fundamental_snapshot", {}) or {}

    cash_label, cash_read, cash_notes = classify_cash_liquidity(f)
    debt_label, debt_read, debt_notes = classify_debt(f)
    prof_label, prof_read, prof_notes = classify_profitability(f)
    growth_label, growth_read, growth_notes = classify_growth(f)
    val_label, val_read, val_notes = classify_valuation(f)
    behavior_label, behavior_read, behavior_notes = classify_market_behavior(f, candidate)
    rate_label, rate_read = classify_rate_sensitivity(debt_label, prof_label, val_label)

    bullish = []
    bearish = []

    if growth_label in ["high_growth", "high_growth_but_earnings_not_following"]:
        bullish.append("Revenue growth is strong.")

    if behavior_label in ["leadership_momentum", "bounce_after_heavy_selloff"]:
        bullish.append("Market behavior shows either leadership or potential dip-buying interest.")

    if cash_label == "cash_rich":
        bullish.append("Cash profile appears strong.")

    if debt_label == "high_leverage":
        bearish.append("High leverage increases risk if rates stay high or cash flow weakens.")

    if prof_label in ["unprofitable", "operating_losses"]:
        bearish.append("Profitability is weak or negative.")

    if val_label in ["expensive_sales_multiple_with_no_earnings", "very_expensive", "expensive"]:
        bearish.append("Valuation requires strong execution and growth confirmation.")

    if behavior_label == "persistent_selloff":
        bearish.append("Price action suggests sustained selling pressure.")

    if not f:
        return {
            "available": False,
            "overall_fundamental_read": "No detailed fundamental snapshot is attached yet. Add Finviz/Finnhub/AlphaVantage fundamentals to improve this section.",
            "cash_profile": "unknown",
            "debt_profile": "unknown",
            "profitability_profile": "unknown",
            "growth_profile": "unknown",
            "valuation_profile": "unknown",
            "rate_sensitivity": "unknown",
            "industry_cycle_read": "unknown",
            "company_adaptation_read": "unknown",
            "market_behavior_read": "unknown",
            "bullish_factors": [],
            "bearish_factors": []
        }

    overall = (
        f"Cash/liquidity: {cash_read} "
        f"Debt: {debt_read} "
        f"Profitability: {prof_read} "
        f"Growth: {growth_read} "
        f"Valuation: {val_read} "
        f"Market behavior: {behavior_read} "
        f"Rate sensitivity: {rate_read}"
    )

    return {
        "available": True,
        "cash_profile": cash_label,
        "cash_read": cash_read,
        "cash_notes": cash_notes,
        "debt_profile": debt_label,
        "debt_read": debt_read,
        "debt_notes": debt_notes,
        "profitability_profile": prof_label,
        "profitability_read": prof_read,
        "profitability_notes": prof_notes,
        "growth_profile": growth_label,
        "growth_read": growth_read,
        "growth_notes": growth_notes,
        "valuation_profile": val_label,
        "valuation_read": val_read,
        "valuation_notes": val_notes,
        "market_behavior_profile": behavior_label,
        "market_behavior_read": behavior_read,
        "market_behavior_notes": behavior_notes,
        "rate_sensitivity": rate_label,
        "rate_sensitivity_read": rate_read,
        "industry_cycle_read": "Use sector leader/peer trend and theme wave phase to determine whether industry is expanding, peaking, or decaying.",
        "company_adaptation_read": "Compare revenue growth, margin trend, and EPS trend to determine whether company is adapting profitably.",
        "bullish_factors": bullish,
        "bearish_factors": bearish,
        "overall_fundamental_read": overall
    }

def enrich_financial_quality(candidate_packet):
    if not isinstance(candidate_packet, dict):
        return candidate_packet

    for c in candidate_packet.get("top_candidates", []):
        c["financial_quality"] = build_financial_quality(c)

    candidate_packet["financial_quality_enriched_at"] = utc_now()

    LATEST.write_text(json.dumps(candidate_packet, indent=2, ensure_ascii=False), encoding="utf-8")
    return candidate_packet

if __name__ == "__main__":
    packet = json.loads(LATEST.read_text(encoding="utf-8"))
    packet = enrich_financial_quality(packet)
    print(json.dumps({
        "status": "complete",
        "candidates": len(packet.get("top_candidates", []))
    }, indent=2))


def recalculate_latest_financial_quality():
    packet = json.loads(LATEST.read_text(encoding="utf-8"))
    packet = enrich_financial_quality(packet)
    return {
        "status": "complete",
        "candidates": len(packet.get("top_candidates", [])),
        "latest": str(LATEST)
    }
