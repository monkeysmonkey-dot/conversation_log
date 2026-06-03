import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
HISTORY = BASE / "features" / "prospect_rank_history.json"
LATEST = BASE / "features" / "latest_candidates.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def load_history():
    try:
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_history(ranks):
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps({
        "timestamp": utc_now(),
        "latest_ranks": ranks
    }, indent=2), encoding="utf-8")

def volume_ramp_from_ratio(volume_ratio):
    v = safe_float(volume_ratio)
    if v >= 1.2:
        return "strong"
    if v >= 1.0:
        return "confirmed"
    if v >= 0.8:
        return "thin"
    return "weak"

def macro_alignment_from_market(market_data):
    macro = market_data.get("macro", {}) if isinstance(market_data, dict) else {}

    spy = macro.get("spy", {})
    qqq = macro.get("qqq", {})
    vix = macro.get("vix", {})
    oil = macro.get("oil", {})

    spy_20 = safe_float(spy.get("change_20d"))
    qqq_20 = safe_float(qqq.get("change_20d"))
    vix_20 = safe_float(vix.get("change_20d"))
    oil_20 = safe_float(oil.get("change_20d"))

    score = 0
    notes = []

    if spy_20 > 0:
        score += 1
        notes.append("SPY positive 20d")
    else:
        notes.append("SPY weak 20d")

    if qqq_20 > 0:
        score += 1
        notes.append("QQQ positive 20d")
    else:
        notes.append("QQQ weak 20d")

    if vix_20 < 0:
        score += 1
        notes.append("VIX declining")
    else:
        notes.append("VIX not declining")

    if oil_20 < -0.05:
        score += 0.5
        notes.append("oil down / disinflationary")
    elif oil_20 > 0.05:
        score -= 0.5
        notes.append("oil up / inflation risk")

    if score >= 2.5:
        return "supportive", notes
    if score >= 1:
        return "mixed", notes
    return "unfavorable", notes

def conviction_from_score(score):
    s = safe_float(score)
    return max(0, min(100, round((s + 5) / 20 * 100, 1)))

def compact_reason(c):
    reason = c.get("reason", "")

    if reason:
        return reason

    pieces = []

    trend = safe_float(c.get("trend_score"))
    rs = safe_float(c.get("relative_strength_vs_spy"))
    vol = safe_float(c.get("volume_ratio"))
    c20 = safe_float(c.get("change_20d"))
    c60 = safe_float(c.get("change_60d"))

    if trend >= 10:
        pieces.append("strong trend")
    elif trend >= 5:
        pieces.append("good trend")
    elif trend < 0:
        pieces.append("weak trend")

    if rs > 0:
        pieces.append("positive relative strength vs SPY")
    elif rs < 0:
        pieces.append("negative relative strength vs SPY")

    if vol >= 1.2:
        pieces.append("volume ramping")
    elif vol >= 1:
        pieces.append("volume confirmed")
    else:
        pieces.append("thin volume")

    if c20 > 0:
        pieces.append("positive 20d momentum")
    if c60 > 0:
        pieces.append("positive 60d momentum")

    return ", ".join(pieces)

def normalize_prospects(candidate_packet, market_data=None, qualitative_data=None, limit=10):
    if not isinstance(candidate_packet, dict):
        return candidate_packet

    candidates = candidate_packet.get("top_candidates", [])
    if not isinstance(candidates, list):
        candidates = []

    history = load_history()
    previous = history.get("latest_ranks", {})

    macro_alignment, macro_notes = macro_alignment_from_market(market_data or {})

    # Sort by candidate_score.
    candidates = sorted(
        candidates,
        key=lambda x: safe_float(x.get("candidate_score")),
        reverse=True
    )[:limit]

    for idx, c in enumerate(candidates, start=1):
        ticker = str(c.get("ticker", "")).upper()
        prev_rank = previous.get(ticker)

        c["ticker"] = ticker
        c["rank"] = idx

        if prev_rank is None:
            c["rank_change"] = "new"
        else:
            try:
                c["rank_change"] = int(prev_rank) - idx
            except Exception:
                c["rank_change"] = 0

        c["candidate_score"] = round(safe_float(c.get("candidate_score")), 3)
        c["trend_score"] = round(safe_float(c.get("trend_score")), 4)
        c["relative_strength_vs_spy"] = round(safe_float(c.get("relative_strength_vs_spy")), 4)
        c["volume_ratio"] = round(safe_float(c.get("volume_ratio")), 4)

        if not c.get("conviction_rate") or safe_float(c.get("conviction_rate")) == 0:
            c["conviction_rate"] = conviction_from_score(c["candidate_score"])

        if not c.get("volume_ramp"):
            c["volume_ramp"] = volume_ramp_from_ratio(c.get("volume_ratio"))

        if not c.get("macro_alignment"):
            c["macro_alignment"] = macro_alignment

        if not c.get("macro_notes"):
            c["macro_notes"] = macro_notes

        if not c.get("whale_signal"):
            c["whale_signal"] = "none"

        if not c.get("policy_geo_risk"):
            c["policy_geo_risk"] = "unknown_or_low"

        if not c.get("qualitative_sentiment"):
            c["qualitative_sentiment"] = "missing"

        if not c.get("filing_forms"):
            c["filing_forms"] = []

        if not c.get("filing_notes"):
            c["filing_notes"] = []

        if not c.get("insider_detail"):
            c["insider_detail"] = []

        c["insider_net_estimated_value"] = safe_float(c.get("insider_net_estimated_value"))
        c["insider_max_transaction_conviction"] = safe_float(c.get("insider_max_transaction_conviction"))

        c["reason"] = compact_reason(c)

    candidate_packet["top_candidates"] = candidates
    candidate_packet["candidate_count"] = len(candidates)
    candidate_packet["normalized_at"] = utc_now()

    save_history({c["ticker"]: c["rank"] for c in candidates})

    LATEST.parent.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(candidate_packet, indent=2, ensure_ascii=False), encoding="utf-8")

    return candidate_packet
