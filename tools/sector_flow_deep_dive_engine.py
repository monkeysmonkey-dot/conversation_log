import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

FLOW = BASE / "features" / "latest_sector_etf_flow.json"
RISK = BASE / "features" / "latest_risk_sentiment.json"
LEADERS = BASE / "data" / "sector_company_leaders.json"

OUT_JSON = BASE / "features" / "latest_sector_flow_deep_dive.json"
OUT_MD = BASE / "reports" / "daily" / "latest_sector_flow_deep_dive.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def safe_float(x):
    try:
        if x in [None, ""]:
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def clamp(value, low=-100.0, high=100.0):
    return max(low, min(high, value))


def score_to_pct(score):
    # Engine raw ETF score is roughly -10 to +10.
    # Convert to signed momentum percent from -100% to +100%.
    return round(clamp(safe_float(score) * 10.0), 1)


def read_label(flow_read):
    text = str(flow_read or "").replace("_", " ")
    if "strong inflow" in text:
        return "Strong inflow"
    if "positive" in text:
        return "Positive"
    if "negative" in text:
        return "Negative"
    if "outflow" in text or "weakness" in text:
        return "Weak / outflow"
    if "missing" in text:
        return "Data missing"
    return "Mixed"


def build_sector_summary(etf_rows, leaders_map):
    sectors = {}

    for row in etf_rows:
        sector = row.get("sector") or "Unknown"
        sectors.setdefault(sector, {
            "sector": sector,
            "etfs": [],
            "score_sum": 0.0,
            "count": 0,
            "positive": 0,
            "negative": 0
        })

        score = safe_float(row.get("momentum_score"))
        pct = score_to_pct(score)

        sectors[sector]["etfs"].append({
            "symbol": row.get("symbol"),
            "region": row.get("region"),
            "momentum_pct": pct,
            "return_5d_pct": round(safe_float(row.get("return_5d")), 2) if row.get("return_5d") is not None else None,
            "rs_spy_5d_pct": round(safe_float(row.get("rs_spy_5d")), 2) if row.get("rs_spy_5d") is not None else None,
            "flow": read_label(row.get("flow_read"))
        })

        sectors[sector]["score_sum"] += pct
        sectors[sector]["count"] += 1

        if pct > 0:
            sectors[sector]["positive"] += 1
        elif pct < 0:
            sectors[sector]["negative"] += 1

    rows = []

    for sector, item in sectors.items():
        avg_pct = round(item["score_sum"] / item["count"], 1) if item["count"] else 0.0
        sorted_etfs = sorted(item["etfs"], key=lambda x: x.get("momentum_pct", 0), reverse=True)

        if avg_pct >= 60:
            read = "Strong leadership"
        elif avg_pct >= 25:
            read = "Positive leadership"
        elif avg_pct <= -50:
            read = "Major laggard"
        elif avg_pct <= -20:
            read = "Weak / lagging"
        else:
            read = "Mixed / neutral"

        rows.append({
            "sector": sector,
            "momentum_pct": avg_pct,
            "read": read,
            "etf_count": item["count"],
            "positive_etfs": item["positive"],
            "negative_etfs": item["negative"],
            "leading_etfs": sorted_etfs[:3],
            "lagging_etfs": sorted(item["etfs"], key=lambda x: x.get("momentum_pct", 0))[:3],
            "top_companies": leaders_map.get("sectors", {}).get(sector, ["Needs mapping", "Needs mapping", "Needs mapping"]),
            "why": explain_sector(sector, avg_pct, item["positive"], item["negative"], item["count"], sorted_etfs[:3])
        })

    return sorted(rows, key=lambda x: x["momentum_pct"], reverse=True)


def explain_sector(sector, avg_pct, positive, negative, count, leading_etfs):
    etf_text = ", ".join([x.get("symbol", "") for x in leading_etfs if x.get("symbol")])

    if avg_pct >= 60:
        return f"{sector} is leading because ETF momentum is strongly positive, {positive}/{count} tracked ETFs are positive, and leaders include {etf_text}."
    if avg_pct >= 25:
        return f"{sector} has positive money-flow confirmation. {positive}/{count} tracked ETFs are positive, led by {etf_text}."
    if avg_pct <= -50:
        return f"{sector} is a major laggard. Negative ETF momentum suggests capital is rotating away or the sector is under pressure."
    if avg_pct <= -20:
        return f"{sector} is lagging. The sector needs confirmation from improved ETF momentum, relative strength, or options/sentiment flow."
    return f"{sector} is mixed. ETF flow does not yet show a clear leadership or laggard signal."


def build_theme_summary(theme_rows, leaders_map):
    out = []

    for row in theme_rows:
        raw_avg = safe_float(row.get("average_score"))
        pct = score_to_pct(raw_avg)

        if pct >= 60:
            read = "Strong theme inflow"
        elif pct >= 25:
            read = "Positive theme flow"
        elif pct <= -50:
            read = "Theme pressure / outflow"
        elif pct <= -20:
            read = "Weak theme flow"
        else:
            read = "Mixed theme flow"

        leaders = row.get("leaders", [])
        leading_etfs = [
            {
                "symbol": x.get("symbol"),
                "momentum_pct": score_to_pct(x.get("score")),
                "flow": read_label(x.get("flow_read"))
            }
            for x in leaders[:3]
        ]

        theme = row.get("theme")

        out.append({
            "theme": theme,
            "momentum_pct": pct,
            "read": read,
            "etfs": row.get("etfs", 0),
            "positive_etfs": row.get("positive_etfs", 0),
            "negative_etfs": row.get("negative_etfs", 0),
            "leading_etfs": leading_etfs,
            "top_companies": leaders_map.get("themes", {}).get(theme, ["Needs mapping", "Needs mapping", "Needs mapping"]),
            "why": explain_theme(theme, pct, leading_etfs)
        })

    return sorted(out, key=lambda x: x["momentum_pct"], reverse=True)


def explain_theme(theme, pct, leading_etfs):
    etf_text = ", ".join([x.get("symbol", "") for x in leading_etfs if x.get("symbol")])

    if pct >= 60:
        return f"{theme} has strong money-flow confirmation. Related ETFs are showing high momentum, led by {etf_text}."
    if pct >= 25:
        return f"{theme} has positive flow, but still needs confirmation from capex, earnings, and source-verified news."
    if pct <= -20:
        return f"{theme} is losing momentum or not currently attracting broad ETF confirmation."
    return f"{theme} is mixed. Watch for stronger ETF participation, capex flow, and verified source evidence."


def build_etf_rows(etf_rows, leaders_map):
    out = []

    for row in etf_rows:
        symbol = row.get("symbol")
        score_pct = score_to_pct(row.get("momentum_score"))

        out.append({
            "etf": symbol,
            "sector": row.get("sector"),
            "region": row.get("region"),
            "momentum_pct": score_pct,
            "return_5d_pct": round(safe_float(row.get("return_5d")), 2) if row.get("return_5d") is not None else None,
            "return_20d_pct": round(safe_float(row.get("return_20d")), 2) if row.get("return_20d") is not None else None,
            "rs_spy_5d_pct": round(safe_float(row.get("rs_spy_5d")), 2) if row.get("rs_spy_5d") is not None else None,
            "volume_ratio": row.get("volume_ratio"),
            "flow": read_label(row.get("flow_read")),
            "themes": row.get("theme_links", []),
            "top_companies": leaders_map.get("etfs", {}).get(symbol, leaders_map.get("sectors", {}).get(row.get("sector"), ["Needs mapping", "Needs mapping", "Needs mapping"])),
            "why": explain_etf(symbol, row)
        })

    return sorted(out, key=lambda x: x["momentum_pct"], reverse=True)


def explain_etf(symbol, row):
    score = safe_float(row.get("momentum_score"))
    r5 = row.get("return_5d")
    rs = row.get("rs_spy_5d")
    vol = row.get("volume_ratio")

    parts = []

    if r5 is not None:
        parts.append(f"5D return {safe_float(r5):+.2f}%")
    if rs is not None:
        parts.append(f"5D relative strength vs SPY {safe_float(rs):+.2f}%")
    if vol is not None:
        parts.append(f"volume ratio {safe_float(vol):.2f}x")

    if score >= 6:
        read = "strong leadership"
    elif score >= 3:
        read = "positive participation"
    elif score <= -5:
        read = "clear weakness"
    elif score <= -2:
        read = "negative participation"
    else:
        read = "mixed participation"

    return f"{symbol} shows {read}. " + "; ".join(parts) + "."


def build_ecosystem_read(theme_summary, sector_summary):
    leading_themes = theme_summary[:5]
    lagging_themes = sorted(theme_summary, key=lambda x: x["momentum_pct"])[:5]

    leading_sectors = sector_summary[:5]
    lagging_sectors = sorted(sector_summary, key=lambda x: x["momentum_pct"])[:5]

    ai_related = [
        x for x in theme_summary
        if any(k in str(x.get("theme", "")).lower() for k in ["ai", "semiconductor", "hbm", "foundry", "packaging", "power", "grid", "nuclear", "software", "cyber"])
    ][:10]

    bullets = []

    if leading_themes:
        bullets.append(f"Leading theme flow is concentrated in {', '.join([x['theme'] for x in leading_themes[:3]])}.")
    if leading_sectors:
        bullets.append(f"Leading sector flow is concentrated in {', '.join([x['sector'] for x in leading_sectors[:3]])}.")
    if lagging_sectors:
        bullets.append(f"Lagging sectors include {', '.join([x['sector'] for x in lagging_sectors[:3]])}.")
    if ai_related:
        bullets.append("AI ecosystem confirmation is strongest where AI-linked ETFs/themes show positive money-flow momentum.")
    bullets.append("This is a money-flow confirmation layer, not a standalone buy/sell signal. Verify with capex, earnings, filings, and source documents.")

    return {
        "leading_themes": leading_themes,
        "lagging_themes": lagging_themes,
        "leading_sectors": leading_sectors,
        "lagging_sectors": lagging_sectors,
        "ai_related_themes": ai_related,
        "why_it_matters": bullets
    }


def main():
    flow = load_json(FLOW, {"etf_rows": [], "theme_rows": []})
    risk = load_json(RISK, {})
    leaders = load_json(LEADERS, {"sectors": {}, "etfs": {}, "themes": {}})

    etf_rows = flow.get("etf_rows", [])
    theme_rows = flow.get("theme_rows", [])

    sector_summary = build_sector_summary(etf_rows, leaders)
    theme_summary = build_theme_summary(theme_rows, leaders)
    etf_deep = build_etf_rows(etf_rows, leaders)
    ecosystem = build_ecosystem_read(theme_summary, sector_summary)

    payload = {
        "timestamp": now_utc(),
        "risk_state": risk.get("risk_state", "unknown"),
        "risk_score_pct": risk.get("risk_score", 0),
        "sector_count": len(sector_summary),
        "theme_count": len(theme_summary),
        "etf_count": len(etf_deep),
        "leading_sector": sector_summary[0] if sector_summary else {},
        "lagging_sector": sorted(sector_summary, key=lambda x: x["momentum_pct"])[0] if sector_summary else {},
        "sector_summary": sector_summary,
        "theme_summary": theme_summary,
        "etf_deep_dive": etf_deep,
        "ecosystem_read": ecosystem,
        "method": {
            "scores": "All displayed money-flow scores are normalized to signed percentages from -100% to +100%.",
            "company_lists": "Company lists are tracking baskets, not verified ETF holdings. Verify official ETF holdings before treating them as composition.",
            "advisory_only": True
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Sector Flow Deep Dive")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Risk state: {payload['risk_state']}")
    lines.append(f"- Risk score: {payload['risk_score_pct']}%")
    lines.append("")
    lines.append("## Why It Matters")
    for item in ecosystem.get("why_it_matters", []):
        lines.append(f"- {item}")

    lines.append("")
    lines.append("## Leading Sectors")
    for item in sector_summary[:8]:
        lines.append(f"- {item['sector']}: {item['momentum_pct']}% | {item['read']} | {item['why']}")

    lines.append("")
    lines.append("## Lagging Sectors")
    for item in sorted(sector_summary, key=lambda x: x["momentum_pct"])[:8]:
        lines.append(f"- {item['sector']}: {item['momentum_pct']}% | {item['read']} | {item['why']}")

    lines.append("")
    lines.append("## Leading Themes")
    for item in theme_summary[:10]:
        lines.append(f"- {item['theme']}: {item['momentum_pct']}% | {item['read']} | companies: {', '.join(item['top_companies'][:3])}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "sectors": len(sector_summary),
        "themes": len(theme_summary),
        "etfs": len(etf_deep),
        "leading_sector": payload["leading_sector"].get("sector"),
        "lagging_sector": payload["lagging_sector"].get("sector"),
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
