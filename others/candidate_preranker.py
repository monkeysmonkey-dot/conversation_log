import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "features" / "latest_candidates.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def score_candidate(ticker, row):
    trend = safe_float(row.get("trend_score"))
    rs = safe_float(row.get("relative_strength_vs_spy"))
    vol_ratio = safe_float(row.get("volume_ratio"))
    change_20d = safe_float(row.get("change_20d"))
    change_60d = safe_float(row.get("change_60d"))
    volatility = safe_float(row.get("volatility_20d"))

    score = 0.0

    # Trend contribution
    score += min(max(trend, -10), 15) * 0.35

    # Relative strength contribution
    score += min(max(rs * 100, -10), 10) * 0.25

    # Momentum contribution
    score += min(max(change_20d * 100, -15), 15) * 0.20
    score += min(max(change_60d * 100, -20), 20) * 0.10

    # Volume confirmation
    if vol_ratio >= 1.2:
        score += 1.0
    elif vol_ratio >= 1.0:
        score += 0.5
    elif vol_ratio < 0.8:
        score -= 0.75

    # Volatility penalty
    if volatility > 0.03:
        score -= 1.0
    elif volatility > 0.02:
        score -= 0.5

    reasons = []

    if trend > 5:
        reasons.append("strong trend")
    if rs > 0:
        reasons.append("positive relative strength vs SPY")
    if vol_ratio >= 1:
        reasons.append("volume confirms")
    else:
        reasons.append("thin volume")
    if change_20d > 0:
        reasons.append("positive 20d momentum")
    if change_60d > 0:
        reasons.append("positive 60d momentum")
    if volatility > 0.02:
        reasons.append("elevated volatility")

    return {
        "ticker": ticker,
        "candidate_score": round(score, 3),
        "trend_score": trend,
        "relative_strength_vs_spy": rs,
        "volume_ratio": vol_ratio,
        "change_20d": change_20d,
        "change_60d": change_60d,
        "volatility_20d": volatility,
        "reason": ", ".join(reasons)
    }

def build_candidates(market_data, qualitative_data=None, limit=3):
    price = market_data.get("price", {}) if isinstance(market_data, dict) else {}

    candidates = []

    for ticker, row in price.items():
        if not isinstance(row, dict):
            continue

        if row.get("error"):
            continue

        candidate = score_candidate(ticker, row)
        candidates.append(candidate)

    candidates = sorted(candidates, key=lambda x: x["candidate_score"], reverse=True)

    payload = {
        "timestamp": utc_now(),
        "top_candidates": candidates[:limit],
        "candidate_count": len(candidates)
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return payload
