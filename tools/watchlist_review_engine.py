import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

WATCH_CANDIDATES = BASE / "data" / "watchlist_candidates.json"
WATCHLIST = BASE / "data" / "user_watchlist.json"
OUT_JSON = BASE / "features" / "latest_watchlist_review.json"
OUT_MD = BASE / "reports" / "daily" / "latest_watchlist_review.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    candidates_packet = load_json(WATCH_CANDIDATES, {"watchlist_candidates": []})
    candidates = candidates_packet.get("watchlist_candidates", [])

    existing = load_json(WATCHLIST, {"watchlist": []})
    existing_items = existing.get("watchlist", [])
    existing_symbols = set([str(x.get("symbol", "")).upper() for x in existing_items])

    pending = []
    already_exists = []

    for item in candidates:
        symbol = str(item.get("symbol", "")).upper()

        if not symbol:
            continue

        if symbol in existing_symbols:
            already_exists.append(item)
        else:
            pending.append(item)

    payload = {
        "timestamp": now_utc(),
        "pending_confirmation": len(pending),
        "already_exists": len(already_exists),
        "pending_items": pending,
        "already_existing_items": already_exists,
        "instruction": "These symbols are not active holdings. Add to watchlist only after user confirmation.",
        "advisory_only": True
    }

    save_json(OUT_JSON, payload)

    lines = []
    lines.append("# Watchlist Review")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Pending confirmation: {payload['pending_confirmation']}")
    lines.append(f"- Already exists: {payload['already_exists']}")
    lines.append("")
    lines.append("## Pending Watchlist Candidates")

    for item in pending[:100]:
        lines.append(f"- {item.get('symbol')} | {item.get('name')} | {item.get('reason')}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "pending_confirmation": len(pending),
        "already_exists": len(already_exists),
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
