from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def normalize_trade(trade):
    if not isinstance(trade, dict):
        return {}

    ticker = trade.get("ticker") or trade.get("symbol") or ""
    side = trade.get("side") or trade.get("action") or ""
    confidence = trade.get("confidence", 0.0)
    allocation_pct = trade.get("allocation_pct", trade.get("position_size", 0.0))

    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0

    try:
        allocation_pct = float(allocation_pct)
    except Exception:
        allocation_pct = 0.0

    return {
        "ticker": str(ticker).upper(),
        "side": str(side).lower(),
        "confidence": confidence,
        "allocation_pct": allocation_pct
    }

def validate_decision(parsed, session="unknown", config=None):
    config = config or {}
    guardrails = config.get("decision_guardrails", {})

    min_watchlist_confidence = float(guardrails.get("min_watchlist_confidence", 0.50))
    min_paper_confidence = float(guardrails.get("min_paper_trade_confidence", 0.65))
    live_trading_enabled = bool(guardrails.get("live_trading_enabled", False))
    paper_trading_enabled = bool(guardrails.get("paper_trading_enabled", True))
    max_position_pct = float(guardrails.get("max_position_pct", 8.0))
    premarket_allows_paper = bool(guardrails.get("premarket_allows_paper", False))
    afterhours_allows_paper = bool(guardrails.get("afterhours_allows_paper", False))

    result = {
        "validated_at": utc_now(),
        "original_action": "unknown",
        "final_action": "NO TRADE",
        "approved_for_live_trading": False,
        "approved_for_paper_trading": False,
        "approved_for_watchlist": True,
        "risk_overrides": [],
        "validated_trades": [],
        "notes": []
    }

    if not isinstance(parsed, dict):
        result["risk_overrides"].append("parsed_output_not_dict")
        return result

    summary = parsed.get("summary", {})
    risk = parsed.get("step_3_risk", {})

    top_trades = summary.get("top_trades", []) if isinstance(summary, dict) else []
    risk_level = summary.get("risk_level", risk.get("risk_level", "unknown"))
    regime = summary.get("regime", "unknown")

    if not isinstance(top_trades, list):
        top_trades = []

    if not top_trades:
        result["final_action"] = "NO TRADE"
        result["risk_overrides"].append("no_top_trades")
        return result

    trade = normalize_trade(top_trades[0])
    result["original_action"] = f"{trade.get('side','')} {trade.get('ticker','')}".strip()

    confidence = trade.get("confidence", 0.0)
    allocation_pct = trade.get("allocation_pct", 0.0)
    session_l = str(session).lower()
    risk_l = str(risk_level).lower()

    if confidence < min_watchlist_confidence:
        result["final_action"] = "NO TRADE"
        result["risk_overrides"].append(f"confidence_below_watchlist_threshold_{confidence}_lt_{min_watchlist_confidence}")

    elif confidence < min_paper_confidence:
        result["final_action"] = "WATCHLIST"
        result["approved_for_watchlist"] = True
        result["risk_overrides"].append(f"confidence_below_threshold_{confidence}_lt_{min_paper_confidence}")

    elif risk_l in ["high", "crisis"]:
        result["final_action"] = "WATCHLIST"
        result["risk_overrides"].append(f"risk_level_blocks_trade_{risk_level}")

    elif session_l == "pre-market" and not premarket_allows_paper:
        result["final_action"] = "WATCHLIST"
        result["risk_overrides"].append("premarket_blocks_paper_trade")

    elif session_l in ["after-hours", "closed", "closed_weekend"] and not afterhours_allows_paper:
        result["final_action"] = "WATCHLIST"
        result["risk_overrides"].append(f"market_session_blocks_paper_trade_{session}")

    elif paper_trading_enabled:
        result["final_action"] = "PAPER_ONLY"
        result["approved_for_paper_trading"] = True

    else:
        result["final_action"] = "WATCHLIST"
        result["risk_overrides"].append("paper_trading_disabled")

    if allocation_pct > max_position_pct:
        result["risk_overrides"].append(f"allocation_capped_{allocation_pct}_to_{max_position_pct}")
        trade["allocation_pct"] = max_position_pct

    # Hard live-trading lock.
    result["approved_for_live_trading"] = False

    if not live_trading_enabled:
        result["notes"].append("Live trading disabled by config. Questrade is data-collection only.")
    else:
        result["notes"].append("Live trading remains blocked by system safety layer.")

    trade["regime"] = regime
    trade["risk_level"] = risk_level
    trade["final_action"] = result["final_action"]

    result["validated_trades"].append(trade)

    return result
