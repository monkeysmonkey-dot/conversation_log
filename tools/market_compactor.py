from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def compact_market(raw):
    if not isinstance(raw, dict):
        return {
            "timestamp": utc_now(),
            "status": "invalid_market_raw",
            "preview": str(raw)[:1000]
        }

    price = raw.get("price", {})
    macro = raw.get("macro", {})

    compact_price = {}

    for symbol, row in price.items():
        if not isinstance(row, dict):
            continue

        compact_price[symbol] = {
            "price": row.get("price"),
            "change_5d": row.get("change_5d"),
            "change_20d": row.get("change_20d"),
            "change_60d": row.get("change_60d"),
            "volume_ratio": row.get("volume_ratio"),
            "volatility_20d": row.get("volatility_20d"),
            "trend_score": row.get("trend_score"),
            "relative_strength_vs_spy": row.get("relative_strength_vs_spy"),
            "error": row.get("error")
        }

    compact_macro = {}

    for name, row in macro.items():
        if not isinstance(row, dict):
            continue

        compact_macro[name] = {
            "ticker": row.get("ticker"),
            "last": row.get("last"),
            "change_5d": row.get("change_5d"),
            "change_20d": row.get("change_20d"),
            "error": row.get("error")
        }

    return {
        "timestamp": raw.get("timestamp", utc_now()),
        "price": compact_price,
        "macro": compact_macro,
        "flow": raw.get("flow", {}),
        "sentiment": raw.get("sentiment", {}),
        "news_status": raw.get("news", {}).get("status") if isinstance(raw.get("news"), dict) else "",
        "catalyst_count": raw.get("catalysts", {}).get("catalyst_count") if isinstance(raw.get("catalysts"), dict) else 0,
        "event_status": raw.get("events", {})
    }
