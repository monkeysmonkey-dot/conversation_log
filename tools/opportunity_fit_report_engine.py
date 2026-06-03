import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

IN_JSON = BASE / "features" / "latest_opportunity_fit.json"
OUT_MD = BASE / "reports" / "daily" / "latest_opportunity_fit_full.md"
OUT_SHORT_MD = BASE / "reports" / "daily" / "latest_opportunity_fit.md"


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


def sort_by_timing(items):
    return sorted(
        items,
        key=lambda x: (
            safe_float(x.get("timing_rank", 99)),
            -safe_float(x.get("timing_adjusted_score_pct")),
            -safe_float(x.get("portfolio_fit_pct")),
        )
    )


def sort_by_portfolio(items):
    return sorted(
        items,
        key=lambda x: (
            -safe_float(x.get("portfolio_fit_pct")),
            -safe_float(x.get("timing_adjusted_score_pct")),
        )
    )


def section(lines, title):
    lines.append("")
    lines.append(f"## {title}")
    lines.append("")


def candidate_block(lines, item, compact=False):
    lines.append(f"### {item.get('candidate')}")
    lines.append(f"- Type: {item.get('candidate_type')}")
    lines.append(f"- Bucket: {item.get('bucket')}")
    lines.append(f"- Timing: {item.get('time_horizon')} / {item.get('time_window')}")
    lines.append(f"- Timing-adjusted score: {item.get('timing_adjusted_score_pct')}%")
    lines.append(f"- Opportunity score: {item.get('opportunity_score_pct')}%")
    lines.append(f"- Portfolio fit: {item.get('portfolio_fit_pct')}% / {item.get('portfolio_fit_read')}")
    lines.append(f"- Money flow: {item.get('money_flow_confirmation_pct')}%")
    lines.append(f"- Capex confirmation: {item.get('capex_confirmation_pct')}%")
    lines.append(f"- Hype risk: {item.get('hype_risk_pct')}%")
    lines.append(f"- Account fit: {item.get('account_fit_read')}")

    why = item.get("why", [])
    if why:
        lines.append("- Why:")
        for reason in why[:3 if compact else 6]:
            if reason:
                lines.append(f"  - {reason}")

    missing = item.get("missing_confirmation", [])
    if missing:
        lines.append("- Missing confirmation:")
        for miss in missing[:3 if compact else 5]:
            lines.append(f"  - {miss}")

    pnotes = item.get("portfolio_fit_reasons", [])
    if pnotes and not compact:
        lines.append("- Portfolio fit notes:")
        for note in pnotes[:4]:
            lines.append(f"  - {note}")

    lines.append("")


def main():
    packet = load_json(IN_JSON, {"ranked_opportunities": []})
    items = packet.get("ranked_opportunities", [])

    lines = []
    lines.append("# Opportunity Fit / Capital Allocation — Full Ranked Report")
    lines.append("")
    lines.append(f"Created: {now_utc()}")
    lines.append(f"- Source risk state: {packet.get('risk_state')}")
    lines.append(f"- Source risk score: {packet.get('risk_score_pct')}%")
    lines.append(f"- Portfolio source: {packet.get('portfolio_source')}")
    lines.append(f"- Total opportunities shown: {len(items)}")
    lines.append("")
    lines.append("> Advisory only. This report ranks opportunities for research, timing, and portfolio fit. It is not an automatic trade instruction.")

    buckets = {}
    for item in items:
        buckets.setdefault(item.get("bucket", "Unknown"), 0)
        buckets[item.get("bucket", "Unknown")] += 1

    section(lines, "Bucket Summary")
    for bucket, count in buckets.items():
        lines.append(f"- {bucket}: {count}")

    timing_ranked = sort_by_timing(items)
    portfolio_ranked = sort_by_portfolio(items)

    section(lines, "Best Timing-Ranked Opportunities")
    for item in timing_ranked[:10]:
        candidate_block(lines, item, compact=True)

    section(lines, "Best Portfolio-Fit Opportunities")
    for item in portfolio_ranked[:10]:
        candidate_block(lines, item, compact=True)

    runners = [
        x for x in items
        if x.get("bucket") in ["Momentum candidate", "Avoid / chase-risk"]
        or safe_float(x.get("money_flow_confirmation_pct")) >= 50
    ]

    section(lines, "Momentum Runners / Chase-Risk Review")
    for item in sort_by_timing(runners):
        candidate_block(lines, item, compact=False)

    laggards = [
        x for x in items
        if x.get("bucket") in ["Watch-only required laggard", "Next rotation watch", "Ecosystem warning"]
        or "laggard" in str(x.get("bucket", "")).lower()
        or "warning" in str(x.get("bucket", "")).lower()
    ]

    section(lines, "Required Laggards / Next-Rotation Watch")
    if laggards:
        for item in sort_by_timing(laggards):
            candidate_block(lines, item, compact=False)
    else:
        lines.append("- No required laggard / next-rotation candidates detected yet.")

    section(lines, "All Opportunities by Timing")
    for item in timing_ranked:
        candidate_block(lines, item, compact=False)

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    # Also overwrite the standard latest report with the enhanced version.
    OUT_SHORT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "opportunities": len(items),
        "full_report": str(OUT_MD),
        "latest_report": str(OUT_SHORT_MD)
    }, indent=2))


if __name__ == "__main__":
    main()
