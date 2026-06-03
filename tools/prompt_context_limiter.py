def limit_market_for_prompt(market):
    if not isinstance(market, dict):
        return {}

    price = market.get("price", {})
    macro = market.get("macro", {})

    # Rank symbols by absolute trend score, keep top 5.
    ranked = []

    for ticker, row in price.items():
        if not isinstance(row, dict):
            continue

        try:
            score = abs(float(row.get("trend_score", 0.0)))
        except Exception:
            score = 0.0

        ranked.append((score, ticker, row))

    ranked = sorted(ranked, reverse=True)[:5]

    compact_price = {}

    for _, ticker, row in ranked:
        compact_price[ticker] = {
            "price": row.get("price"),
            "change_20d": row.get("change_20d"),
            "change_60d": row.get("change_60d"),
            "volume_ratio": row.get("volume_ratio"),
            "trend_score": row.get("trend_score"),
            "relative_strength_vs_spy": row.get("relative_strength_vs_spy")
        }

    compact_macro = {}

    for k, row in macro.items():
        if not isinstance(row, dict):
            continue

        compact_macro[k] = {
            "last": row.get("last"),
            "change_20d": row.get("change_20d")
        }

    return {
        "timestamp": market.get("timestamp"),
        "price_top": compact_price,
        "macro": compact_macro,
        "news_status": market.get("news_status"),
        "catalyst_count": market.get("catalyst_count")
    }


def limit_qual_for_prompt(qual):
    if not isinstance(qual, dict):
        return {}

    out = {
        "routing": qual.get("routing", {}),
        "gdelt_geopolitical": {},
        "sec_filings": {},
        "fred_macro": {},
        "alphavantage": {},
        "financial_news": {},
        "transcripts": {},
        "press_releases": {}
    }

    # GDELT: only statuses + first article title per theme.
    gdelt = qual.get("gdelt_geopolitical", {})
    themes = gdelt.get("themes", {}) if isinstance(gdelt, dict) else {}

    out["gdelt_geopolitical"] = {
        "provider": gdelt.get("provider", "gdelt") if isinstance(gdelt, dict) else "gdelt",
        "status": gdelt.get("status", "") if isinstance(gdelt, dict) else "",
        "themes": {}
    }

    for theme, payload in themes.items():
        articles = payload.get("articles", []) if isinstance(payload, dict) else []
        out["gdelt_geopolitical"]["themes"][theme] = {
            "status": payload.get("status", "") if isinstance(payload, dict) else "",
            "top_title": articles[0].get("title", "")[:180] if articles else ""
        }

    # SEC: keep only most recent 3 filings per symbol.
    sec = qual.get("sec_filings", {})
    filings = sec.get("recent_material_filings", {}) if isinstance(sec, dict) else {}

    out["sec_filings"] = {
        "provider": "sec",
        "status": sec.get("status", "") if isinstance(sec, dict) else "",
        "recent_material_filings": {}
    }

    for ticker, rows in filings.items():
        out["sec_filings"]["recent_material_filings"][ticker] = rows[:3] if isinstance(rows, list) else []

    # FRED: latest only.
    fred = qual.get("fred_macro", {})
    latest_macro = fred.get("latest_macro", {}) if isinstance(fred, dict) else {}

    out["fred_macro"] = {
        "provider": "fred",
        "status": fred.get("status", "") if isinstance(fred, dict) else "",
        "latest_macro": {}
    }

    for name, payload in latest_macro.items():
        latest = payload.get("latest") if isinstance(payload, dict) else None
        out["fred_macro"]["latest_macro"][name] = {
            "latest": latest
        }

    # AlphaVantage: keep company overview + one top news item per symbol.
    av = qual.get("alphavantage", {})
    av_news = av.get("news_sentiment_summary", []) if isinstance(av, dict) else []
    av_overview = av.get("company_overview_summary", {}) if isinstance(av, dict) else {}

    out["alphavantage"] = {
        "provider": "alphavantage",
        "status": av.get("status", "") if isinstance(av, dict) else "",
        "company_overview_summary": {},
        "news_sentiment_summary": []
    }

    for ticker, row in av_overview.items():
        if not isinstance(row, dict):
            continue

        out["alphavantage"]["company_overview_summary"][ticker] = {
            "Sector": row.get("Sector"),
            "Industry": row.get("Industry"),
            "PERatio": row.get("PERatio"),
            "ForwardPE": row.get("ForwardPE"),
            "QuarterlyRevenueGrowthYOY": row.get("QuarterlyRevenueGrowthYOY"),
            "QuarterlyEarningsGrowthYOY": row.get("QuarterlyEarningsGrowthYOY"),
            "Beta": row.get("Beta"),
            "PercentInstitutions": row.get("PercentInstitutions")
        }

    for block in av_news[:3]:
        symbol = block.get("symbol", "")
        top_items = block.get("top_items", [])

        item = top_items[0] if top_items else {}

        out["alphavantage"]["news_sentiment_summary"].append({
            "symbol": symbol,
            "top_item": {
                "title": item.get("title", "")[:180],
                "overall_sentiment_label": item.get("overall_sentiment_label"),
                "overall_sentiment_score": item.get("overall_sentiment_score"),
                "summary": item.get("summary", "")[:220]
            }
        })

    # Simple statuses only.
    for key in ["financial_news", "transcripts", "press_releases"]:
        block = qual.get(key, {})
        out[key] = {
            "provider": block.get("provider", key) if isinstance(block, dict) else key,
            "status": block.get("status", "") if isinstance(block, dict) else ""
        }

    return out


def limit_memory_for_prompt(memory):
    if not isinstance(memory, dict):
        return {}

    return {
        "mode": memory.get("mode"),
        "cash": memory.get("cash"),
        "positions": memory.get("positions", {}),
        "watchlist": memory.get("watchlist", []),
        "agent_scores": memory.get("agent_scores", {}),
        "recent_runs": memory.get("recent_runs", [])[-3:]
    }


def limit_config_for_prompt(config):
    if not isinstance(config, dict):
        return {}

    return {
        "risk_limits": config.get("risk_limits", {}),
        "signal_thresholds": config.get("signal_thresholds", {}),
        "decision_guardrails": config.get("decision_guardrails", {})
    }
