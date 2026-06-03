def bulletize_summary(parsed, decision_validation=None):
    if not isinstance(parsed, dict):
        return parsed

    summary = parsed.get("summary", {})
    if not isinstance(summary, dict):
        return parsed

    brief = summary.get("human_readable_brief", "")

    # If already point-form, keep it.
    if isinstance(brief, str) and brief.strip().startswith("- "):
        return parsed

    decision_validation = decision_validation or {}

    regime = summary.get("regime", "unknown")
    risk = summary.get("risk_level", "unknown")
    confidence = summary.get("confidence", 0.0)
    top_trades = summary.get("top_trades", [])
    watchlist = summary.get("watchlist_updates", [])

    final_action = decision_validation.get("final_action", "unknown")
    risk_overrides = decision_validation.get("risk_overrides", [])

    if top_trades:
        main_setup = str(top_trades[0])
    else:
        main_setup = "No formal top_trades candidate."

    if watchlist:
        watchlist_text = ", ".join([str(x) for x in watchlist[:5]])
    else:
        watchlist_text = "None."

    if risk_overrides:
        blocked_text = ", ".join([str(x) for x in risk_overrides[:5]])
    else:
        blocked_text = "No deterministic override listed."

    parsed["summary"]["human_readable_brief"] = (
        f"- Regime: {regime}\n"
        f"- Decision: {final_action}\n"
        f"- Main setup: {main_setup}\n"
        f"- Why approved/blocked: {blocked_text}\n"
        f"- Risk notes: Risk level {risk}; confidence {confidence}.\n"
        f"- Watchlist: {watchlist_text}\n"
        f"- Next review: Reassess on next scheduled run."
    )

    return parsed
