
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
BROWSER_CFG = BASE / "config" / "browser_source_config.json"
SOURCE_ROUTER_CFG = BASE / "config" / "source_router_config.json"

DEFAULT_ROUTER = {
    "task_intent_routes": {
        "macro_qualitative_followup": {
            "primary_sources": ["investing", "biztoc", "perplexity"],
            "fallback_sources": ["terminal_x", "finviz"],
            "max_sources": 3,
            "intent": ["macro_event", "market_news", "macro_narrative"]
        },
        "association_intelligence_followup": {
            "primary_sources": ["perplexity", "terminal_x", "biztoc"],
            "fallback_sources": ["finviz", "investing"],
            "max_sources": 3,
            "intent": ["company_association", "theme_explanation", "policy_reasoning"]
        },
        "institutional_flow_followup": {
            "primary_sources": ["hedgefollow_tracker", "hedgefollow_largest_buys"],
            "fallback_sources": ["finviz", "perplexity"],
            "max_sources": 3,
            "intent": ["institutional_flow", "hedge_fund_buys", "13f_context"]
        },
        "insider_flow_followup": {
            "primary_sources": ["hedgefollow_insider", "hedgefollow_largest_insider_buys"],
            "fallback_sources": ["finviz", "perplexity"],
            "max_sources": 3,
            "intent": ["insider_tracking", "insider_buying", "form4_context"]
        },
        "congress_policy_followup": {
            "primary_sources": ["hedgefollow_congress", "perplexity", "biztoc"],
            "fallback_sources": ["terminal_x", "finviz"],
            "max_sources": 3,
            "intent": ["congressional_trading", "policy_maker_trades", "policy_reasoning"]
        },
        "fundamental_company_followup": {
            "primary_sources": ["finviz", "terminal_x", "perplexity"],
            "fallback_sources": ["biztoc", "webull_watch"],
            "max_sources": 3,
            "intent": ["fundamentals", "valuation", "market_structure", "competitive_position"]
        },
        "routine_macro_qualitative_scan": {
            "primary_sources": ["investing", "biztoc", "perplexity"],
            "fallback_sources": ["terminal_x"],
            "max_sources": 3,
            "intent": ["market_news", "macro_narrative", "headline_momentum"]
        }
    },
    "keyword_intent_rules": [
        {"keywords": ["insider", "form 4", "executive buying", "largest insider"], "route": "insider_flow_followup"},
        {"keywords": ["hedge fund", "13f", "institutional buying", "largest hedge"], "route": "institutional_flow_followup"},
        {"keywords": ["congress", "senator", "representative", "politician"], "route": "congress_policy_followup"},
        {"keywords": ["fed", "powell", "fomc", "rates", "cpi", "oil", "dollar", "treasury", "macro"], "route": "macro_qualitative_followup"},
        {"keywords": ["p/e", "valuation", "margin", "debt", "cash", "fundamental", "market share", "monopoly"], "route": "fundamental_company_followup"},
        {"keywords": ["ceo", "interview", "appeared with", "mentioned", "partnered", "association", "supply chain"], "route": "association_intelligence_followup"}
    ]
}

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def ensure_router_config():
    if not SOURCE_ROUTER_CFG.exists():
        save_json(SOURCE_ROUTER_CFG, DEFAULT_ROUTER)
    return load_json(SOURCE_ROUTER_CFG, DEFAULT_ROUTER)

def available_source_ids():
    cfg = load_json(BROWSER_CFG, {})
    return {s.get("id") for s in cfg.get("sources", []) if s.get("id")}

def infer_route_from_task(task):
    router = ensure_router_config()
    task_type = task.get("task_type", "")

    if task_type in router.get("task_intent_routes", {}):
        return task_type

    blob = " ".join([
        str(task.get("task_type", "")),
        str(task.get("reason", "")),
        str(task.get("why_it_matters", "")),
        str(task.get("association_type", "")),
        " ".join(task.get("entities", [])),
        str(task.get("instruction", ""))
    ]).lower()

    for rule in router.get("keyword_intent_rules", []):
        for kw in rule.get("keywords", []):
            if kw.lower() in blob:
                return rule.get("route")

    return "association_intelligence_followup"

def select_sources_for_task(task):
    router = ensure_router_config()
    source_ids = available_source_ids()

    route_key = infer_route_from_task(task)
    route = router.get("task_intent_routes", {}).get(route_key, {})

    max_sources = int(route.get("max_sources", 3))
    selected = []
    reasons = []

    for sid in route.get("primary_sources", []):
        if sid in source_ids and sid not in selected:
            selected.append(sid)
            reasons.append(f"{sid}: primary source for {route_key}")

    if len(selected) < max_sources:
        for sid in route.get("fallback_sources", []):
            if sid in source_ids and sid not in selected:
                selected.append(sid)
                reasons.append(f"{sid}: fallback source for {route_key}")
            if len(selected) >= max_sources:
                break

    return {
        "route": route_key,
        "intent": route.get("intent", []),
        "selected_sources": selected[:max_sources],
        "selection_reason": reasons[:max_sources],
        "max_sources": max_sources
    }

def select_sources_for_queue(tasks):
    enriched = []
    unique_sources = []

    for task in tasks:
        task = dict(task)
        selection = select_sources_for_task(task)
        task["source_selection"] = selection
        task["suggested_sources"] = selection.get("selected_sources", [])

        for sid in task["suggested_sources"]:
            if sid not in unique_sources:
                unique_sources.append(sid)

        enriched.append(task)

    return {
        "tasks": enriched,
        "unique_sources": unique_sources
    }

if __name__ == "__main__":
    ensure_router_config()
    print(json.dumps({
        "status": "ok",
        "router_config": str(SOURCE_ROUTER_CFG)
    }, indent=2))
