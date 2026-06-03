import json
from pathlib import Path

BASE = Path(r"C:\Users\Abe\hermes agent\project\stock manager")
path = BASE / "config" / "system_config.json"

with open(path, "r", encoding="utf-8-sig") as f:
    cfg = json.load(f)

cfg["decision_guardrails"] = {
    "min_watchlist_confidence": 0.50,
    "min_paper_trade_confidence": 0.65,
    "min_live_trade_confidence": 0.80,
    "live_trading_enabled": False,
    "paper_trading_enabled": True,
    "max_position_pct": 8.0,
    "premarket_allows_paper": False,
    "afterhours_allows_paper": False,
    "require_catalyst_for_paper": False,
    "require_flow_for_paper": False
}

with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)

print("system_config.json updated with decision_guardrails.")
