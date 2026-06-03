ï»¿import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

ACTION_QUEUE = BASE / "features" / "latest_universal_action_queue.json"
RISK = BASE / "features" / "latest_risk_sentiment.json"
OPPORTUNITY = BASE / "features" / "latest_opportunity_fit.json"
SCHEDULE = BASE / "features" / "latest_manual_schedule_status.json"
BRINGUP = BASE / "features" / "latest_bring_up_to_speed.json"
PORTFOLIO = BASE / "data" / "portfolio_snapshot.json"
RESEARCH_DB = BASE / "data" / "research_database.json"
THESIS_DB = BASE / "data" / "thesis_database.json"

OUT_JSON = BASE / "features" / "latest_mobile_console_summary.json"


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


def money(value):
    try:
        return "${:,.0f}".format(float(value))
    except Exception:
        return "$0"


def top_candidates(opportunity_packet):
    candidates = opportunity_packet.get("ranked_opportunities", []) or opportunity_packet.get("ranked_candidates", [])
    return candidates[:10]


def portfolio_summary(portfolio):
    positions = portfolio.get("positions", {})
    holdings = portfolio.get("holdings", [])
    lots = portfolio.get("lots", [])

    position_count = len(positions) if isinstance(positions, dict) else 0
    lots_count = len(lots) if isinstance(lots, list) else 0

    stock_value = 0.0
    retirement_value = 0.0
    cad_native = 0.0
    usd_native = 0.0
    needs_sorting = 0

    if isinstance(positions, dict):
        for item in positions.values():
            if not isinstance(item, dict):
                continue

            mv = safe_float(item.get("market_value"))
            acct = str(item.get("account_type", "")).lower()
            currency = str(item.get("currency", "")).upper()

            if item.get("needs_account_sorting"):
                needs_sorting += 1

            if "company retirement" in acct or "retirement" in acct:
                retirement_value += mv
            else:
                stock_value += mv

            if currency == "CAD":
                cad_native += mv
            elif currency == "USD":
                usd_native += mv

    total_cad_display = stock_value + retirement_value

    return {
        "total_cad_display": total_cad_display,
        "stock_accounts_cad_display": stock_value,
        "company_retirement_cad_display": retirement_value,
        "cad_native_value": cad_native,
        "usd_native_value": usd_native,
        "positions_detected": position_count,
        "lots_detected": lots_count,
        "needs_account_sorting": needs_sorting,
        "currency_note": "CAD total shown as main total. CAD/USD original currencies preserved. Stock accounts and company retirement remain separate."
    }


def report_status():
    report_paths = {
        "macro": BASE / "reports" / "daily" / "latest_market_console_trends.md",
        "micro": BASE / "reports" / "daily" / "latest_theme_rotation_intelligence.md",
        "premarket": BASE / "reports" / "daily" / "latest_decision_replay.md",
        "trend": BASE / "reports" / "daily" / "latest_opportunity_fit.md",
    }

    out = {}
    for key, path in report_paths.items():
        out[key] = {
            "exists": path.exists(),
            "status": "Updated" if path.exists() else "Missing",
            "path": str(path)
        }

    # Keep this human-readable and compact.
    out["summary_bullets"] = [
import os
API_KEY = os.getenv("API_KEY")
        "Software/cybersecurity leadership is currently prominent.",
        "AI infrastructure still needs capex/source confirmation before conviction upgrade."
    ]

    return out


def market_trend_diagram(risk_state):
    return [
        risk_state or "Unknown",
        "â†“",
        "Software / Cybersecurity leadership",
        "â†“",
        "AI infrastructure theme",
        "â†“",
        "Power/Grid and capex confirmation watch"
    ]


def main():
    queue = load_json(ACTION_QUEUE, {})
    risk = load_json(RISK, {})
    opportunity = load_json(OPPORTUNITY, {})
    schedule = load_json(SCHEDULE, {})
    bringup = load_json(BRINGUP, {})
    portfolio = load_json(PORTFOLIO, {})
    research = load_json(RESEARCH_DB, {})
    thesis = load_json(THESIS_DB, {})

    candidates = top_candidates(opportunity)
    top = candidates[0] if candidates else {}

    port = portfolio_summary(portfolio)

    schedule_blocks = []
    for block in schedule.get("blocks", []):
        schedule_blocks.append({
            "label": block.get("label"),
            "status": block.get("status"),
            "icon": block.get("status_icon"),
            "color": block.get("color")
        })

    research_sources = len(research.get("sources", [])) if isinstance(research.get("sources", []), list) else 0
    thesis_sources = len(thesis.get("sources", [])) if isinstance(thesis.get("sources", []), list) else 0

    risk_state = risk.get("risk_state", "unknown")

    payload = {
        "timestamp": now_utc(),
        "system_snapshot": {
            "last_refresh": bringup.get("timestamp", "not run"),
            "refresh_status": bringup.get("status", "unknown"),
            "risk_state": risk_state,
            "risk_score": risk.get("risk_score", 0),
            "portfolio_status": "Portfolio sorting" if port["needs_account_sorting"] else "Portfolio OK",
            "items_needing_review": queue.get("total_items", 0),
            "api_throttle_status": "Enabled"
        },
        "portfolio_accounts": port,
        "action_queue": {
            "total_items": queue.get("total_items", 0),
            "high_priority": queue.get("high_priority", 0),
            "counts": queue.get("counts", {}),
            "items": queue.get("items", [])[:20]
        },
        "opportunity_snapshot": {
            "top_timing_opportunity": top.get("candidate", "None"),
            "top_bucket": top.get("bucket", ""),
            "top_score": top.get("timing_adjusted_score_pct", top.get("opportunity_score_pct", "")),
            "portfolio_fit": top.get("portfolio_fit_read", ""),
            "warning": "Needs confirmation" if top else "No opportunity data"
        },
        "top_10_opportunities": [
            {
                "rank": i + 1,
                "candidate": item.get("candidate"),
                "score": item.get("timing_adjusted_score_pct", item.get("opportunity_score_pct", "")),
                "bucket": item.get("bucket"),
                "fit": item.get("portfolio_fit_read", "")
            }
            for i, item in enumerate(candidates)
        ],
        "reports": report_status(),
        "market_trend_diagram": market_trend_diagram(risk_state),
        "scheduler_status": schedule_blocks,
        "references_supporting_evidence": {
            "research_sources": research_sources,
            "thesis_sources": thesis_sources,
            "official_evidence": len([x for x in research.get("sources", []) if isinstance(x, dict) and x.get("usable_as_evidence")]),
            "needs_verification": len([x for x in thesis.get("sources", []) if isinstance(x, dict) and x.get("verification_required")]),
            "note": "Human-readable references only. Raw JSON/code/debug remains hidden."
        },
        "report_summaries": {
            "macro": [
import os
API_KEY = os.getenv("API_KEY")
                "Use macro as a filter, not a standalone buy/sell signal."
            ],
            "premarket": [
                "Watch software/cybersecurity leadership.",
                "Avoid chasing crowded AI winners without capex/source support."
            ],
            "portfolio": [
                "Stock accounts and company retirement remain separate.",
                "Account sorting must be completed before tax/account conclusions are reliable."
            ]
        },
        "advisory_only": True
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "review_items": payload["action_queue"]["total_items"],
        "top_opportunity": payload["opportunity_snapshot"]["top_timing_opportunity"],
        "positions": payload["portfolio_accounts"]["positions_detected"],
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()