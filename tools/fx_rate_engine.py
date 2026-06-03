import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

OUT_JSON = BASE / "features" / "latest_fx_rates.json"
OUT_MD = BASE / "reports" / "daily" / "latest_fx_rates.md"
MANUAL_FX = BASE / "data" / "manual_fx_rates.json"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def fetch_boc_usd_cad():
    try:
        url = "https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8", errors="ignore"))

        observations = data.get("observations", [])
        if not observations:
            return None

        latest = observations[-1]
        value = latest.get("FXUSDCAD", {}).get("v")
        date = latest.get("d")

        rate = float(value)

        return {
            "pair": "USD/CAD",
            "rate": rate,
            "date": date,
            "source": "Bank of Canada",
            "verified": True
        }
    except Exception as e:
        return {
            "pair": "USD/CAD",
            "rate": None,
            "date": "",
            "source": "Bank of Canada",
            "verified": False,
            "error": str(e)
        }


def main():
    manual = load_json(MANUAL_FX, {})
    boc = fetch_boc_usd_cad()

    usd_cad = None
    source_read = ""

    if boc and boc.get("rate"):
        usd_cad = boc["rate"]
        source_read = "Using Bank of Canada USD/CAD rate."
    else:
        manual_rate = manual.get("USD_CAD")
        try:
            usd_cad = float(manual_rate)
            source_read = "Using manual USD/CAD fallback rate."
        except Exception:
            usd_cad = None
            source_read = "No usable USD/CAD rate found."

    rates = {
        "CAD_CAD": 1.0,
        "USD_CAD": usd_cad,
        "CAD_USD": round(1 / usd_cad, 8) if usd_cad else None
    }

    payload = {
        "timestamp": now_utc(),
        "base_currency": "CAD",
        "rates": rates,
        "source_read": source_read,
        "sources": {
            "bank_of_canada": boc,
            "manual_fx_file": str(MANUAL_FX)
        },
        "usage_note": "Use CAD as reporting/base currency. Preserve account currency and security currency separately."
    }

    save_json(OUT_JSON, payload)

    lines = []
    lines.append("# FX Rate Snapshot")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append(f"- Base currency: CAD")
    lines.append(f"- USD/CAD: {rates.get('USD_CAD')}")
    lines.append(f"- Source read: {source_read}")
    lines.append("")
    lines.append("## Usage")
    lines.append("- Account currency and security currency are tracked separately.")
    lines.append("- CAD reporting totals use FX conversion.")
    lines.append("- Company retirement account balances should remain separate from stock account balances.")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "USD_CAD": rates.get("USD_CAD"),
        "source": source_read,
        "json": str(OUT_JSON),
        "report": str(OUT_MD)
    }, indent=2))


if __name__ == "__main__":
    main()
