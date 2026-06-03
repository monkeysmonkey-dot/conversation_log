import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
CANDIDATES = BASE / "features" / "latest_candidates.json"
THEME_JSON = BASE / "features" / "latest_theme_wave_analysis.json"
OUT = BASE / "reports" / "weekly" / "latest_sunday_investment_planning.md"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def discipline_read(c, theme_item=None):
    conviction = float(c.get("conviction_rate", 0) or 0)
    vol = float(c.get("volume_ratio", 0) or 0)
    rank_change = c.get("rank_change")
    phase = theme_item.get("phase", {}) if theme_item else {}
    bubble = phase.get("bubble_risk", "unknown")
    fomo = phase.get("fomo_risk", "unknown")

    if conviction >= 80 and vol < 1:
        stance = "strong_watch_but_wait_for_participation"
        note = "High conviction but thin volume. Avoid FOMO until participation confirms."
    elif conviction >= 80 and vol >= 1:
        stance = "constructive_with_risk_control"
        note = "Strong conviction and better volume. Still use validator/guardrails."
    elif conviction < 65:
        stance = "watchlist_only"
        note = "Below paper threshold. Needs stronger confirmation."
    else:
        stance = "confirmation_needed"
        note = "Good enough to track, not enough to force entry."

    return {
        "stance": stance,
        "note": note,
        "bubble_risk": bubble,
        "fomo_risk": fomo,
        "rank_change": rank_change
    }

def main():
    candidates = load_json(CANDIDATES, {}).get("top_candidates", [])
    theme = load_json(THEME_JSON, {})
    theme_lookup = {x.get("ticker"): x for x in theme.get("theme_wave_items", [])}

    OUT.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Sunday Investment Planning / Next-Week Thesis")
    lines.append("")
    lines.append(f"Created: {utc_now()}")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("- Re-rank prospects.")
    lines.append("- Determine theme phase.")
    lines.append("- Review bubble/crowding/recession risk.")
    lines.append("- Decide watch/add/wait/take-profit posture for next week.")
    lines.append("- Keep live trading disabled. Paper trading only if validator approves.")
    lines.append("")

    lines.append("## Next Week Watchlist")
    lines.append("")

    for c in candidates[:10]:
        t = c.get("ticker")
        theme_item = theme_lookup.get(t, {})
        read = discipline_read(c, theme_item)

        lines.append(f"### {t}")
        lines.append("")
        lines.append(f"- Conviction rate: {c.get('conviction_rate')}%")
        lines.append(f"- Candidate score: {c.get('candidate_score')}")
        lines.append(f"- Rank change: {c.get('rank_change')}")
        lines.append(f"- Investment discipline stance: {read['stance']}")
        lines.append(f"- Interpretation: {read['note']}")
        lines.append(f"- FOMO risk: {read['fomo_risk']}")
        lines.append(f"- Bubble risk: {read['bubble_risk']}")
        lines.append(f"- Macro alignment: {c.get('macro_alignment')}")
        lines.append(f"- Volume ramp: {c.get('volume_ramp')}")
        lines.append(f"- Whale / filing signal: {c.get('whale_signal')}")
        lines.append("")
        lines.append("Upgrade triggers:")
        lines.append("- Volume ratio improves above 1.0 or 1.2.")
        lines.append("- Catalyst/news confirms the move.")
        lines.append("- Sentiment improves.")
        lines.append("- Related peers/beneficiaries confirm the theme.")
        lines.append("- Insider/institutional transaction detail improves conviction.")
        lines.append("")
        lines.append("Downgrade / take-profit triggers:")
        lines.append("- Rank deteriorates.")
        lines.append("- Volume fades.")
        lines.append("- Sector leader rolls over.")
        lines.append("- Bubble/crowding risk rises.")
        lines.append("- Macro alignment weakens.")
        lines.append("")

    lines.append("## Portfolio Discipline Reminder")
    lines.append("")
    lines.append("- Avoid chasing if move is extended and confirmation is weak.")
    lines.append("- Avoid being greedy if theme is crowded or rank starts deteriorating.")
    lines.append("- Do not assume every leader creates broad-sector opportunity.")
    lines.append("- Look for laggers only when the relationship chain and peer confirmation support it.")
    lines.append("- Deterministic validator remains final authority.")

    OUT.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "report": str(OUT)
    }, indent=2))

if __name__ == "__main__":
    main()
