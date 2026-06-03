import os
import json
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

BASE = Path(__file__).resolve().parents[1]
CACHE_DIR = BASE / "qualitative" / "official" / "gdelt"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / "gdelt_cache.json"

QUERIES = {
    "geopolitical_risk": "war conflict sanctions tariff election military",
    "energy_risk": "oil supply disruption OPEC refinery outage",
    "policy_risk": "regulation antitrust export controls trade policy tariffs"
}

def utc_now():
    return datetime.now(timezone.utc)

def load_cache():
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

def save_cache(data):
    try:
        CACHE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

def cache_is_fresh(cache, minutes=120):
    try:
        ts = datetime.fromisoformat(cache.get("timestamp"))
        return utc_now() - ts < timedelta(minutes=minutes)
    except Exception:
        return False

def run(force=False):
    enabled = os.getenv("GDELT_ENABLED", "true").lower() == "true"

    if not enabled:
        return {
            "provider": "gdelt",
            "status": "disabled",
            "themes": {},
            "timestamp": utc_now().isoformat()
        }

    cache = load_cache()

    if cache and cache_is_fresh(cache, minutes=120) and not force:
        cache["status"] = "cached"
        return cache

    max_records = int(os.getenv("GDELT_MAX_RECORDS", "3"))
    timespan = os.getenv("GDELT_TIMESPAN", "12h")

    results = {}

    for name, query in QUERIES.items():
        try:
            url = "https://api.gdeltproject.org/api/v2/doc/doc"
            params = {
                "query": query,
                "mode": "ArtList",
                "format": "json",
                "maxrecords": max_records,
                "timespan": timespan
            }

            # Short timeout so GDELT never blocks the whole system.
            r = requests.get(url, params=params, timeout=6)

            if r.status_code == 429:
                results[name] = {
                    "status": "rate_limited",
                    "articles": []
                }
                continue

            r.raise_for_status()
            data = r.json()
            articles = data.get("articles", [])

            cleaned = []
            for a in articles[:max_records]:
                cleaned.append({
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "domain": a.get("domain", ""),
                    "sourceCountry": a.get("sourceCountry", ""),
                    "seendate": a.get("seendate", "")
                })

            results[name] = {
                "status": "ok",
                "articles": cleaned
            }

        except Exception as e:
            results[name] = {
                "status": "error",
                "error": str(e)[:300],
                "articles": []
            }

    payload = {
        "provider": "gdelt",
        "status": "ok",
        "themes": results,
        "timestamp": utc_now().isoformat()
    }

    save_cache(payload)
    return payload

if __name__ == "__main__":
    print(json.dumps(run(force=True), indent=2, ensure_ascii=False))
