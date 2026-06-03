ï»¿import csv
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

SECTOR_FLOW = BASE / "features" / "latest_sector_etf_flow.json"
MANUAL_OPTIONS = BASE / "data" / "manual_options_flow.csv"
MANUAL_SENTIMENT = BASE / "data" / "manual_market_sentiment.csv"
DOCUMENT_INTAKE = BASE / "features" / "latest_document_intake.json"

OUT_JSON = BASE / "features" / "latest_risk_sentiment.json"
OUT_MD = BASE / "reports" / "daily" / "latest_risk_sentiment.md"


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


def read_csv(path):
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def pct_change(values, lookback):
    try:
        if len(values) <= lookback:
            return None
        old = float(values[-1 - lookback])
        new = float(values[-1])
        if old == 0:
            return None
        return ((new - old) / old) * 100
    except Exception:
        return None


def fetch_market_prices():
    symbols = ["SPY", "QQQ", "IWM", "TLT", "HYG", "LQD", "GLD", "UUP", "^VIX"]

    try:
        import yfinance as yf
    except Exception:
        return {}, "yfinance_missing"

    try:
        hist = yf.download(
            tickers=" ".join(symbols),
            period="90d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True
        )

        out = {}

        for symbol in symbols:
            try:
                close = hist[(symbol, "Close")].dropna().tolist()
                if close:
                    out[symbol] = [float(x) for x in close]
            except Exception:
                continue

        return out, "yfinance"

    except Exception as e:
        return {}, f"price_fetch_error: {e}"


def classify_risk_state(score):
    if score >= 35:
import os
API_KEY = os.getenv("API_KEY")
    if score >= 10:
import os
API_KEY = os.getenv("API_KEY")
    if score <= -35:
import os
API_KEY = os.getenv("API_KEY")
    if score <= -10:
import os
API_KEY = os.getenv("API_KEY")
    return "âšª Neutral / Mixed"


def add_component(components, name, score, weight, reason):
    components.append({
        "component": name,
        "score": score,
        "weight": weight,
        "weighted": score * weight,
        "reason": reason
    })


def market_price_components(price_data):
    components = []

    spy5 = pct_change(price_data.get("SPY", []), 5)
    qqq5 = pct_change(price_data.get("QQQ", []), 5)
    iwm5 = pct_change(price_data.get("IWM", []), 5)
    tlt5 = pct_change(price_data.get("TLT", []), 5)
    hyg5 = pct_change(price_data.get("HYG", []), 5)
    lqd5 = pct_change(price_data.get("LQD", []), 5)
    vix = price_data.get("^VIX", [])
    vix_last = vix[-1] if vix else None
    vix5 = pct_change(vix, 5)

    equity_score = 0
    equity_notes = []

    for label, value in [("SPY", spy5), ("QQQ", qqq5), ("IWM", iwm5)]:
        if value is None:
            continue
        if value > 1:
            equity_score += 1
        elif value < -1:
            equity_score -= 1
        equity_notes.append(f"{label} 5D {value:+.2f}%")

    equity_score = max(-2, min(2, equity_score))
    add_component(
        components,
        "Equity Momentum",
        equity_score,
        3,
        "; ".join(equity_notes) if equity_notes else "Equity data missing."
    )

    credit_score = 0
    if hyg5 is not None and lqd5 is not None:
        spread = hyg5 - lqd5
        if spread > 1:
            credit_score = 2
        elif spread > 0.25:
            credit_score = 1
        elif spread < -1:
            credit_score = -2
        elif spread < -0.25:
            credit_score = -1
        reason = f"HYG 5D {hyg5:+.2f}% vs LQD 5D {lqd5:+.2f}%."
    else:
        reason = "Credit ETF data missing."

    add_component(components, "Credit Appetite", credit_score, 2, reason)

    rate_score = 0
    if tlt5 is not None and spy5 is not None:
        # Strong TLT up while equities weak often means defensive/rate fear.
        if spy5 > 0 and tlt5 < 1:
            rate_score = 1
        elif spy5 < 0 and tlt5 > 1:
            rate_score = -1
        reason = f"TLT 5D {tlt5:+.2f}%, SPY 5D {spy5:+.2f}%."
    else:
        reason = "Rate/defensive data missing."

    add_component(components, "Rates / Defensive Tilt", rate_score, 1.5, reason)

    vix_score = 0
    if vix_last is not None:
        if vix_last < 16:
            vix_score += 2
        elif vix_last < 20:
            vix_score += 1
        elif vix_last > 28:
            vix_score -= 2
        elif vix_last > 22:
            vix_score -= 1

        if vix5 is not None:
            if vix5 > 10:
                vix_score -= 1
            elif vix5 < -10:
                vix_score += 1

        vix_score = max(-2, min(2, vix_score))
        reason = f"VIX {vix_last:.2f}; 5D change {vix5:+.2f}%" if vix5 is not None else f"VIX {vix_last:.2f}."
    else:
        reason = "VIX data missing."

    add_component(components, "Volatility Regime", vix_score, 3, reason)

    return components


def sector_flow_components(sector_packet):
    components = []

    etf_rows = sector_packet.get("etf_rows", [])

    if not etf_rows:
        add_component(components, "Sector / ETF Flow", 0, 3, "Sector ETF flow data missing.")
        return components

    positive = len([x for x in etf_rows if safe_float(x.get("momentum_score")) > 0])
    negative = len([x for x in etf_rows if safe_float(x.get("momentum_score")) < 0])
    total = len(etf_rows)

    breadth = (positive - negative) / total if total else 0

    if breadth >= 0.35:
        score = 2
    elif breadth >= 0.15:
        score = 1
    elif breadth <= -0.35:
        score = -2
    elif breadth <= -0.15:
        score = -1
    else:
        score = 0

    add_component(
        components,
        "Sector / ETF Flow",
        score,
        3,
        f"{positive} positive ETF reads vs {negative} negative ETF reads out of {total}."
    )

    cyclical_sectors = {
        "Technology",
        "Consumer Discretionary",
        "Industrials",
        "Financials",
        "Semiconductors",
        "Energy",
        "Infrastructure",
        "Grid Infrastructure",
        "Robotics / AI",
    }

    defensive_sectors = {
        "Utilities",
        "Consumer Staples",
        "Healthcare",
        "Real Estate",
    }

    cyc = [safe_float(x.get("momentum_score")) for x in etf_rows if x.get("sector") in cyclical_sectors]
    defens = [safe_float(x.get("momentum_score")) for x in etf_rows if x.get("sector") in defensive_sectors]

    cyc_avg = sum(cyc) / len(cyc) if cyc else 0
    def_avg = sum(defens) / len(defens) if defens else 0
    rotation = cyc_avg - def_avg

    if rotation >= 2:
        rot_score = 2
    elif rotation >= 0.75:
        rot_score = 1
    elif rotation <= -2:
        rot_score = -2
    elif rotation <= -0.75:
        rot_score = -1
    else:
        rot_score = 0

    add_component(
        components,
        "Cyclical vs Defensive Rotation",
        rot_score,
        2,
        f"Cyclical avg score {cyc_avg:.2f} vs defensive avg score {def_avg:.2f}."
    )

    return components


def options_flow_component():
    rows = read_csv(MANUAL_OPTIONS)

    if not rows:
        return [{
            "component": "Options Flow",
            "score": 0,
            "weight": 1.5,
            "weighted": 0,
            "reason": "No manual options flow rows yet."
        }]

    call_premium = sum(safe_float(x.get("call_premium")) for x in rows)
    put_premium = sum(safe_float(x.get("put_premium")) for x in rows)
    call_volume = sum(safe_float(x.get("call_volume")) for x in rows)
    put_volume = sum(safe_float(x.get("put_volume")) for x in rows)

    total_premium = call_premium + put_premium
    total_volume = call_volume + put_volume

    if total_premium > 0:
        call_share = call_premium / total_premium
    elif total_volume > 0:
        call_share = call_volume / total_volume
    else:
        call_share = 0.5

    if call_share >= 0.70:
        score = 2
    elif call_share >= 0.58:
        score = 1
    elif call_share <= 0.30:
        score = -2
    elif call_share <= 0.42:
        score = -1
    else:
        score = 0

    return [{
        "component": "Options Flow",
        "score": score,
        "weight": 1.5,
        "weighted": score * 1.5,
        "reason": f"Manual options call share {call_share * 100:.1f}% across {len(rows)} rows."
    }]


def sentiment_component():
    rows = read_csv(MANUAL_SENTIMENT)

    if not rows:
        return {
            "score": 0,
            "sentiment_read": "no_manual_sentiment",
            "average_sentiment": 0,
            "verified_rows": 0,
            "unverified_rows": 0,
            "reason": "No manual sentiment rows yet."
        }

    verified_scores = []
    unverified = 0

    for row in rows:
        score = safe_float(row.get("sentiment_score"))
        verification_required = str(row.get("verification_required", "true")).lower() in ["true", "yes", "1", "required"]

        if verification_required:
            unverified += 1
        else:
            verified_scores.append(score)

    all_scores = [safe_float(x.get("sentiment_score")) for x in rows]
    avg_all = sum(all_scores) / len(all_scores) if all_scores else 0
    avg_verified = sum(verified_scores) / len(verified_scores) if verified_scores else avg_all

    if avg_verified >= 0.45:
        read = "positive_sentiment"
        score = 1
    elif avg_verified <= -0.45:
        read = "negative_sentiment"
        score = -1
    else:
        read = "mixed_sentiment"
        score = 0

    return {
        "score": score,
        "sentiment_read": read,
        "average_sentiment": round(avg_verified, 3),
        "verified_rows": len(verified_scores),
        "unverified_rows": unverified,
        "reason": f"Average verified/manual sentiment {avg_verified:+.2f}; unverified rows {unverified}."
    }


def document_quality_warning():
    packet = load_json(DOCUMENT_INTAKE, {"documents": []})
    docs = packet.get("documents", [])

    if not docs:
        return {
            "unverified_documents": 0,
            "warning": "No uploaded document sentiment/evidence pressure detected."
        }

    unverified = 0

    for doc in docs:
        suggestion = doc.get("suggestion", {})
        if suggestion.get("verification_required", True):
            unverified += 1

    if unverified > 0:
        warning = "Some uploaded documents require verification before being treated as evidence."
    else:
        warning = "Uploaded documents appear to be confirmed/source-type or no verification warning is present."

    return {
        "unverified_documents": unverified,
        "warning": warning
    }


def main():
    sector_packet = load_json(SECTOR_FLOW, {})
    price_data, price_source = fetch_market_prices()

    components = []
    components.extend(market_price_components(price_data))
    components.extend(sector_flow_components(sector_packet))
    components.extend(options_flow_component())

    sentiment = sentiment_component()
    add_component(
        components,
        "Manual Sentiment",
        sentiment["score"],
        1,
        sentiment["reason"]
    )

    total_weight = sum(safe_float(x.get("weight")) for x in components)
    weighted_sum = sum(safe_float(x.get("weighted")) for x in components)

    # Each component score is roughly -2 to +2.
    risk_score = (weighted_sum / (total_weight * 2)) * 100 if total_weight > 0 else 0
    risk_score = round(risk_score, 2)

    risk_state = classify_risk_state(risk_score)
    docs = document_quality_warning()

    payload = {
        "timestamp": now_utc(),
        "risk_score": risk_score,
        "risk_state": risk_state,
        "price_source": price_source,
        "components": components,
        "sentiment": sentiment,
        "document_quality": docs,
        "summary": {
            "read": risk_state,
            "explanation": "Risk score blends index momentum, credit appetite, volatility, sector ETF flow, options flow, and manual sentiment.",
            "advisory_only": True
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
import os
API_KEY = os.getenv("API_KEY")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Risk state: {risk_state}")
    lines.append(f"- Risk score: {risk_score}")
    lines.append(f"- Price source: {price_source}")
    lines.append("")
    lines.append("## Components")
    for c in components:
        lines.append(f"- {c.get('component')}: score {c.get('score')} | {c.get('reason')}")
    lines.append("")
    lines.append("## Sentiment")
    lines.append(f"- {sentiment.get('sentiment_read')}: {sentiment.get('reason')}")
    lines.append("")
    lines.append("## Document Quality")
    lines.append(f"- {docs.get('warning')}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "risk_state": risk_state,
        "risk_score": risk_score,
        "price_source": price_source,
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()