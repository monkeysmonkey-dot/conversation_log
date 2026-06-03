import json
from pathlib import Path

BASE = Path(r"C:\Users\Abe\hermes agent\project\stock manager")
path = BASE / "config" / "data_sources.json"

with open(path, "r", encoding="utf-8-sig") as f:
    cfg = json.load(f)

rules = cfg.setdefault("source_rules", {})

rules["manual_upload"] = {
    "tier": 1,
    "enabled": True,
    "role": "manual transcript/document upload fallback",
    "requires_key": False,
    "fallback_only": False
}

rules["sec_13f"] = {
    "tier": 2,
    "enabled": True,
    "role": "SEC 13F institutional holdings",
    "requires_key": False,
    "fallback_only": False
}

rules["sec_form4"] = {
    "tier": 2,
    "enabled": True,
    "role": "SEC Form 4 insider transactions",
    "requires_key": False,
    "fallback_only": False
}

rules["finra_short"] = {
    "tier": 2,
    "enabled": True,
    "role": "FINRA short volume and short interest",
    "requires_key": True,
    "fallback_only": False
}

rules["cftc_cot"] = {
    "tier": 2,
    "enabled": True,
    "role": "CFTC Commitments of Traders futures positioning",
    "requires_key": False,
    "fallback_only": False
}

rules["congressional_trading"] = {
    "tier": 2,
    "enabled": True,
    "role": "Congressional trading disclosure data",
    "requires_key": False,
    "fallback_only": False
}

with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)

print("data_sources.json patched with missing source rules.")
