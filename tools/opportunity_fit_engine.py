import csv
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

THEME_ROTATION = BASE / "features" / "latest_theme_rotation_intelligence.json"
DEEP_FLOW = BASE / "features" / "latest_sector_flow_deep_dive.json"
RISK = BASE / "features" / "latest_risk_sentiment.json"
MANUAL_CANDIDATES = BASE / "data" / "manual_opportunity_candidates.csv"

PORTFOLIO_CANDIDATES = [
    BASE / "data" / "portfolio_snapshot.json",
    BASE / "features" / "latest_portfolio_snapshot.json",
    BASE / "data" / "account_portfolio_snapshot.json",
    BASE / "features" / "latest_account_portfolio_snapshot.json",
]

OUT_JSON = BASE / "features" / "latest_opportunity_fit.json"
OUT_MD = BASE / "reports" / "daily" / "latest_opportunity_fit.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def read_csv(path):
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def safe_float(value):
    try:
        if value in [None, ""]:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def load_portfolio_context():
    """
    Generic portfolio reader.
    Works even if snapshot schema changes by recursively searching for symbol/ticker keys.
    Later this should be replaced with the official portfolio/account schema.
    """
    context = {
        "source": None,
        "symbols": set(),
        "symbol_values": {},
        "accounts": set(),
        "notes": []
    }

    packet = None
    source = None

    for path in PORTFOLIO_CANDIDATES:
        if path.exists():
            packet = load_json(path, {})
            source = str(path)
            break

    if not packet:
        context["notes"].append("No portfolio snapshot found. Portfolio fit uses placeholder logic.")
        return context

    context["source"] = source

    def walk(obj):
        if isinstance(obj, dict):
            symbol = (
                obj.get("symbol")
                or obj.get("ticker")
                or obj.get("Symbol")
                or obj.get("Ticker")
            )

            if isinstance(symbol, str) and 1 <= len(symbol.strip()) <= 12:
                sym = symbol.strip().upper()
                context["symbols"].add(sym)

                val = (
                    obj.get("market_value")
                    or obj.get("marketValue")
                    or obj.get("value")
                    or obj.get("current_value")
                    or obj.get("Current Value")
                )
                if val is not None:
                    context["symbol_values"][sym] = context["symbol_values"].get(sym, 0.0) + safe_float(val)

            account = obj.get("account") or obj.get("account_name") or obj.get("account_type")
            if isinstance(account, str):
                context["accounts"].add(account)

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(packet)

    if not context["symbols"]:
        context["notes"].append("Portfolio snapshot loaded, but no symbols were detected.")

    return context


def portfolio_fit(candidate, portfolio):
    """
    Portfolio-aware placeholder.
    Uses actual held symbols if found, but does not yet calculate full CAD/USD/account/tax weights.
    """
    held = portfolio.get("symbols", set())
    candidate_symbol = str(candidate.get("symbol", "") or "").upper()
    companies = [str(x).upper() for x in candidate.get("top_companies", [])]

    overlap = []

    if candidate_symbol and candidate_symbol in held:
        overlap.append(candidate_symbol)

    for company in companies:
        if company in held:
            overlap.append(company)

    overlap = sorted(set(overlap))

    score = 55.0
    reasons = []

    if not portfolio.get("source"):
        reasons.append("No portfolio snapshot detected; portfolio fit is preliminary.")
        score = 50.0
    else:
        reasons.append(f"Portfolio snapshot detected: {portfolio.get('source')}.")

    if overlap:
        score -= 10
        reasons.append("Existing exposure detected: " + ", ".join(overlap[:6]) + ". This may be an add-on/hold review rather than fresh exposure.")
    else:
        score += 10
        reasons.append("No direct symbol/company overlap detected in current portfolio snapshot; may improve diversification if thesis confirms.")

    if candidate.get("bucket") in ["Avoid / chase-risk", "Ecosystem warning"]:
        score -= 15
        reasons.append("Portfolio fit reduced because timing/chase-risk is unfavorable.")

    if candidate.get("bucket") in ["Next rotation watch", "Long-term buildout candidate"]:
        score += 8
        reasons.append("Portfolio fit improved because candidate may represent a required ecosystem layer or longer-duration opportunity.")

    score = round(clamp(score), 1)

    if score >= 70:
        read = "good_fit_if_confirmed"
    elif score >= 55:
        read = "moderate_fit"
    elif score <= 40:
        read = "poor_fit_or_overlap_risk"
    else:
        read = "neutral_fit"

    return {
        "portfolio_fit_pct": score,
        "portfolio_fit_read": read,
        "portfolio_overlap": overlap,
        "portfolio_fit_reasons": reasons
    }


def timing_bucket_from_scores(
    opportunity_type,
    money_flow,
    completion,
    capex,
    innovation,
    hype,
    is_current_winner=False,
    is_required_laggard=False,
    is_next_rotation=False,
    is_warning=False
):
    if is_warning and capex < 25:
        return {
            "bucket": "Ecosystem warning",
            "timing_rank": 5,
            "time_horizon": "wait",
            "time_window": "wait for confirmation",
            "timing_read": "Important layer, but lack of capex/money-flow confirmation makes it a warning rather than an entry signal."
        }

    if is_current_winner and hype >= 65:
        return {
            "bucket": "Avoid / chase-risk",
            "timing_rank": 4,
            "time_horizon": "acute/crowded",
            "time_window": "days to weeks",
            "timing_read": "Strong runner, but high hype/crowding risk means avoid blindly chasing."
        }

    if is_next_rotation:
        return {
            "bucket": "Next rotation watch",
            "timing_rank": 1,
            "time_horizon": "rotation watch",
            "time_window": "weeks to quarters",
            "timing_read": "Required ecosystem layer may become attractive if capex and market money continue confirming."
        }

    if is_required_laggard and capex < 35:
        return {
            "bucket": "Watch-only required laggard",
            "timing_rank": 3,
            "time_horizon": "watch",
            "time_window": "wait for capex / flow turn",
            "timing_read": "Required layer is lagging. This can become opportunity only after confirmation improves."
        }

    if innovation >= 60 and completion >= 55 and capex >= 35:
        return {
            "bucket": "Long-term buildout candidate",
            "timing_rank": 2,
            "time_horizon": "long-term",
            "time_window": "quarters to years",
            "timing_read": "Theme/layer has stronger long-term characteristics with better ecosystem/capex support."
        }

    if money_flow >= 50 and hype < 60:
        return {
            "bucket": "Momentum candidate",
            "timing_rank": 2,
            "time_horizon": "near-term",
            "time_window": "days to months",
            "timing_read": "Money flow is supportive, but confirmation and portfolio fit still matter."
        }

    return {
        "bucket": "Needs confirmation",
        "timing_rank": 3,
        "time_horizon": "unclear",
        "time_window": "monitor",
        "timing_read": "Candidate needs stronger commonality across money flow, ecosystem, capex, and portfolio fit."
    }


def missing_confirmation(candidate):
    missing = []

    if safe_float(candidate.get("capex_confirmation_pct")) < 35:
        missing.append("Verified capex / contract / filing evidence.")

    if safe_float(candidate.get("ecosystem_completion_pct")) < 55:
        missing.append("Higher ecosystem completion or bottleneck resolution.")

    if safe_float(candidate.get("money_flow_confirmation_pct")) < 25:
        missing.append("Money-flow confirmation from ETF/sector/options/sentiment.")

    if safe_float(candidate.get("hype_risk_pct")) >= 65:
        missing.append("Reduced crowding / better valuation / better entry timing.")

    if candidate.get("bucket") in ["Watch-only required laggard", "Ecosystem warning"]:
        missing.append("Proof that lagging required layer is turning from warning into opportunity.")

    if not missing:
        missing.append("Continue monitoring for invalidation and source-confirmed updates.")

    return missing


def build_theme_candidate(theme):
    money = safe_float(theme.get("money_flow_confirmation_pct"))
    completion = safe_float(theme.get("ecosystem_completion_pct"))
    capex = safe_float(theme.get("capex_confirmation_pct"))
    innovation = safe_float(theme.get("innovation_reality_pct"))
    hype = safe_float(theme.get("hype_risk_pct"))

    has_current = bool(theme.get("current_winners"))
    has_next = bool(theme.get("next_rotation_candidates"))
    has_warning = bool(theme.get("warning_layers"))

    timing = timing_bucket_from_scores(
        opportunity_type="theme",
        money_flow=money,
        completion=completion,
        capex=capex,
        innovation=innovation,
        hype=hype,
        is_current_winner=has_current,
        is_required_laggard=bool(theme.get("required_lagging_layers")),
        is_next_rotation=has_next,
        is_warning=has_warning
    )

    score = (
        innovation * 0.25
        + max(money, 0) * 0.20
        + completion * 0.15
        + capex * 0.15
        - hype * 0.15
        + (10 if has_next else 0)
    )

    if has_warning:
        score -= 8

    score = round(clamp(score), 1)

    return {
        "candidate": theme.get("theme"),
        "candidate_type": "theme",
        "symbol": "",
        "opportunity_score_pct": score,
        "money_flow_confirmation_pct": money,
        "ecosystem_completion_pct": completion,
        "capex_confirmation_pct": capex,
        "innovation_reality_pct": innovation,
        "hype_risk_pct": hype,
        "rotation_stage": theme.get("rotation_stage"),
        "current_winners": theme.get("current_winners", []),
        "required_lagging_layers": theme.get("required_lagging_layers", []),
        "next_rotation_candidates": theme.get("next_rotation_candidates", []),
        "warning_layers": theme.get("warning_layers", []),
        "top_companies": [],
        "why": theme.get("interpretation", []),
        "advisory_only": True,
        **timing
    }


def build_layer_candidates(theme):
    out = []
    theme_name = theme.get("theme")
    hype = safe_float(theme.get("hype_risk_pct"))
    innovation = safe_float(theme.get("innovation_reality_pct"))

    for layer in theme.get("layer_results", []):
        layer_name = layer.get("layer")
        money = safe_float(layer.get("money_flow_pct"))
        completion = safe_float(layer.get("completion_pct"))
        capex = safe_float(layer.get("capex_confirmation_pct"))
        status = layer.get("status")

        is_current = status == "current_winner"
        is_required_laggard = status == "lagging_required_layer"
        is_next = status == "possible_next_rotation"
        is_warning = status == "ecosystem_warning"

        timing = timing_bucket_from_scores(
            opportunity_type="ecosystem_layer",
            money_flow=money,
            completion=completion,
            capex=capex,
            innovation=innovation,
            hype=hype,
            is_current_winner=is_current,
            is_required_laggard=is_required_laggard,
            is_next_rotation=is_next,
            is_warning=is_warning
        )

        importance = safe_float(layer.get("importance"))
        score = (
            max(money, 0) * 0.20
            + completion * 0.15
            + capex * 0.20
            + innovation * 0.15
            + importance * 3
            - hype * 0.10
        )

        if is_next:
            score += 15
        if is_warning:
            score -= 15
        if is_required_laggard and capex < 25:
            score -= 5

        score = round(clamp(score), 1)

        why = [
            f"{layer_name} belongs to {theme_name}.",
            f"Money flow is {money:.1f}%, completion is {completion:.1f}%, capex confirmation is {capex:.1f}%.",
            f"Layer status: {status}.",
            "Failure if missing: " + str(layer.get("failure_if_missing", "")),
            "Success signal: " + str(layer.get("success_signal", "")),
        ]

        out.append({
            "candidate": f"{theme_name} / {layer_name}",
            "candidate_type": "ecosystem_layer",
            "theme": theme_name,
            "symbol": "",
            "opportunity_score_pct": score,
            "money_flow_confirmation_pct": money,
            "ecosystem_completion_pct": completion,
            "capex_confirmation_pct": capex,
            "innovation_reality_pct": innovation,
            "hype_risk_pct": hype,
            "layer_status": status,
            "sector_match": layer.get("sector_match", []),
            "top_companies": [],
            "why": why,
            "advisory_only": True,
            **timing
        })

    return out


def build_etf_candidates(deep):
    out = []

    for item in deep.get("etf_deep_dive", []):
        money = safe_float(item.get("momentum_pct"))
        hype = 0.0
        innovation = 50.0
        completion = 50.0
        capex = 0.0

        is_current = money >= 60
        is_warning = money <= -50

        timing = timing_bucket_from_scores(
            opportunity_type="etf",
            money_flow=money,
            completion=completion,
            capex=capex,
            innovation=innovation,
            hype=hype,
            is_current_winner=is_current,
            is_required_laggard=False,
            is_next_rotation=False,
            is_warning=is_warning
        )

        score = (
            max(money, 0) * 0.40
            + safe_float(item.get("return_5d_pct")) * 1.5
            + safe_float(item.get("rs_spy_5d_pct")) * 1.5
            + 35
        )

        if is_warning:
            score -= 20

        score = round(clamp(score), 1)

        out.append({
            "candidate": item.get("etf"),
            "candidate_type": "etf",
            "symbol": item.get("etf"),
            "sector": item.get("sector"),
            "region": item.get("region"),
            "themes": item.get("themes", []),
            "opportunity_score_pct": score,
            "money_flow_confirmation_pct": money,
            "ecosystem_completion_pct": completion,
            "capex_confirmation_pct": capex,
            "innovation_reality_pct": innovation,
            "hype_risk_pct": hype,
            "return_5d_pct": item.get("return_5d_pct"),
            "rs_spy_5d_pct": item.get("rs_spy_5d_pct"),
            "top_companies": item.get("top_companies", []),
            "why": [item.get("why", "")],
            "advisory_only": True,
            **timing
        })

    return out


def manual_candidates():
    rows = read_csv(MANUAL_CANDIDATES)
    out = []

    for row in rows:
        if not any(row.values()):
            continue

        verified = str(row.get("verified", "")).lower() in ["true", "yes", "1", "verified"]

        out.append({
            "candidate": row.get("symbol_or_theme", ""),
            "candidate_type": row.get("candidate_type", "manual"),
            "symbol": row.get("symbol_or_theme", ""),
            "opportunity_score_pct": 0,
            "bucket": "Manual review",
            "timing_rank": 3,
            "time_horizon": row.get("time_horizon", "manual"),
            "time_window": "manual review",
            "timing_read": "Manual candidate requires verification and engine classification.",
            "account_hint": row.get("account_hint", ""),
            "thesis": row.get("thesis", ""),
            "source": row.get("source", ""),
            "verified": verified,
            "notes": row.get("notes", ""),
            "why": ["Manual candidate requires source verification and connection to theme/sector/portfolio context."],
            "missing_confirmation": ["Verify source and map to ecosystem layer."],
            "advisory_only": True
        })

    return out


def account_fit(candidate):
    horizon = candidate.get("time_horizon", "")

    if horizon in ["acute/crowded", "near-term"]:
        return {
            "account_fit_read": "tactical_review_required",
            "suggested_account_review": "Review taxable impact, position size, and risk controls before acting.",
            "tax_notes": "Shorter-term candidates need tighter timing and tax review."
        }

    if horizon == "long-term":
        return {
            "account_fit_read": "long_term_account_review",
            "suggested_account_review": "Review TFSA/RRSP/FHSA/cash suitability based on growth, dividends, currency, concentration, and contribution room.",
            "tax_notes": "Long-term candidates may fit registered accounts if concentration and volatility are acceptable."
        }

    if horizon == "rotation watch":
        return {
            "account_fit_read": "watchlist_before_account_decision",
            "suggested_account_review": "Wait for confirmation before assigning account placement.",
            "tax_notes": "Do not force account placement until money-flow/capex confirmation improves."
        }

    return {
        "account_fit_read": "needs_review",
        "suggested_account_review": "Needs portfolio/account/tax context before account placement.",
        "tax_notes": "No tax/account conclusion yet."
    }


def enrich_candidates(candidates, portfolio):
    enriched = []

    for candidate in candidates:
        pfit = portfolio_fit(candidate, portfolio)
        candidate.update(pfit)
        candidate.update(account_fit(candidate))
        candidate["missing_confirmation"] = missing_confirmation(candidate)

        # Timing-adjusted score: opportunity score + portfolio fit, with timing rank penalty.
        candidate["timing_adjusted_score_pct"] = round(clamp(
            safe_float(candidate.get("opportunity_score_pct")) * 0.65
            + safe_float(candidate.get("portfolio_fit_pct")) * 0.25
            + (6 - safe_float(candidate.get("timing_rank"))) * 2.0
        ), 1)

        enriched.append(candidate)

    return enriched


def main():
    rotation = load_json(THEME_ROTATION, {"themes": []})
    deep = load_json(DEEP_FLOW, {})
    risk = load_json(RISK, {})
    portfolio = load_portfolio_context()

    all_candidates = []

    for theme in rotation.get("themes", []):
        all_candidates.append(build_theme_candidate(theme))
        all_candidates.extend(build_layer_candidates(theme))

    all_candidates.extend(build_etf_candidates(deep))
    all_candidates.extend(manual_candidates())

    all_candidates = enrich_candidates(all_candidates, portfolio)

    ranked = sorted(
        all_candidates,
        key=lambda x: (
            safe_float(x.get("timing_rank")),
            -safe_float(x.get("timing_adjusted_score_pct"))
        )
    )

    buckets = {}
    for item in ranked:
        bucket = item.get("bucket", "Unknown")
        buckets[bucket] = buckets.get(bucket, 0) + 1

    payload = {
        "timestamp": now_utc(),
        "risk_state": risk.get("risk_state", "unknown"),
        "risk_score_pct": risk.get("risk_score", 0),
        "portfolio_source": portfolio.get("source"),
        "portfolio_symbols_detected": sorted(list(portfolio.get("symbols", set()))),
        "candidate_count": len(ranked),
        "buckets": buckets,
        "ranked_opportunities": ranked,
        "method": {
            "purpose": "Show all opportunities and rank them by timing, money flow, ecosystem importance, capex confirmation, hype risk, and current portfolio fit.",
            "portfolio_fit": "Uses detected portfolio symbols if a portfolio snapshot exists; full CAD/USD/account/tax weighting comes in the next portfolio integration phase.",
            "advisory_only": True
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Opportunity Fit / Capital Allocation")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Risk state: {payload['risk_state']}")
    lines.append(f"- Risk score: {payload['risk_score_pct']}%")
    lines.append(f"- Portfolio source: {payload['portfolio_source']}")
    lines.append(f"- Candidates shown: {payload['candidate_count']}")
    lines.append("")
    lines.append("## Bucket Summary")
    for bucket, count in buckets.items():
        lines.append(f"- {bucket}: {count}")

    lines.append("")
    lines.append("## Ranked Opportunities")
    for item in ranked:
        lines.append("")
        lines.append(f"### {item.get('candidate')}")
        lines.append(f"- Type: {item.get('candidate_type')}")
        lines.append(f"- Timing-adjusted score: {item.get('timing_adjusted_score_pct')}%")
        lines.append(f"- Opportunity score: {item.get('opportunity_score_pct')}%")
        lines.append(f"- Bucket: {item.get('bucket')}")
        lines.append(f"- Timing: {item.get('time_horizon')} / {item.get('time_window')}")
        lines.append(f"- Portfolio fit: {item.get('portfolio_fit_pct')}% / {item.get('portfolio_fit_read')}")
        lines.append(f"- Money flow: {item.get('money_flow_confirmation_pct')}%")
        lines.append(f"- Capex confirmation: {item.get('capex_confirmation_pct')}%")
        lines.append(f"- Hype risk: {item.get('hype_risk_pct')}%")
        lines.append(f"- Account fit: {item.get('account_fit_read')}")
        lines.append("- Why:")
        for reason in item.get("why", [])[:6]:
            if reason:
                lines.append(f"  - {reason}")
        lines.append("- Missing confirmation:")
        for miss in item.get("missing_confirmation", [])[:5]:
            lines.append(f"  - {miss}")
        if item.get("portfolio_fit_reasons"):
            lines.append("- Portfolio fit notes:")
            for reason in item.get("portfolio_fit_reasons", [])[:4]:
                lines.append(f"  - {reason}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "candidates": len(ranked),
        "top_candidate": ranked[0].get("candidate") if ranked else None,
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
