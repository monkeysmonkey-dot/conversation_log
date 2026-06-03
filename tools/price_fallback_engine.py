import csv
import json
import math
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

PORTFOLIO_SNAPSHOT = BASE / "data" / "portfolio_snapshot.json"
BATCH_CSV = BASE / "data" / "replay_price_updates.csv"
REPLAY_PATH = BASE / "features" / "latest_decision_replay.json"

OUT_JSON = BASE / "features" / "latest_price_snapshot.json"
OUT_MD = BASE / "reports" / "daily" / "latest_price_snapshot.md"


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


def safe_float(value):
    try:
        if value in [None, ""]:
            return None
        value = float(value)
        if math.isnan(value) or value <= 0:
            return None
        return value
    except Exception:
        return None


def fetch_text(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def fetch_json(url, timeout=10):
    return json.loads(fetch_text(url, timeout=timeout))


def read_csv_rows(path):
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def get_target_tickers():
    tickers = set()

    replay = load_json(REPLAY_PATH, {})
    for ticker in replay.get("tickers_missing_current_price", []):
        if ticker:
            tickers.add(str(ticker).upper())

    portfolio = load_json(PORTFOLIO_SNAPSHOT, {})
    for ticker in portfolio.get("positions", {}).keys():
        if ticker:
            tickers.add(str(ticker).upper())

    for row in read_csv_rows(BATCH_CSV):
        ticker = str(row.get("ticker", "")).strip().upper()
        if ticker:
            tickers.add(ticker)

    return sorted(tickers)


def manual_sources(ticker):
    sources = []

    portfolio = load_json(PORTFOLIO_SNAPSHOT, {})
    pos = portfolio.get("positions", {}).get(ticker, {})
    portfolio_price = safe_float(pos.get("current_price"))
    if portfolio_price is not None:
        sources.append({
            "source": "portfolio_snapshot",
            "price": portfolio_price,
            "timestamp": pos.get("updated_at") or portfolio.get("updated_at"),
            "source_type": "manual_saved",
            "quality": "not_verification_source"
        })

    for row in read_csv_rows(BATCH_CSV):
        row_ticker = str(row.get("ticker", "")).strip().upper()
        if row_ticker == ticker:
            batch_price = safe_float(row.get("current_price"))
            if batch_price is not None:
                sources.append({
                    "source": "batch_csv",
                    "price": batch_price,
                    "timestamp": now_utc(),
                    "source_type": "manual_batch",
                    "quality": "not_verification_source"
                })

    return sources


def source_yahoo(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1m"
        data = fetch_json(url)
        result = data.get("chart", {}).get("result", [])
        if not result:
            return {
                "source": "yahoo_chart",
                "price": None,
                "source_type": "external",
                "quality": "failed",
                "error": "No chart result"
            }

        meta = result[0].get("meta", {})
        price = safe_float(meta.get("regularMarketPrice") or meta.get("previousClose"))

        return {
            "source": "yahoo_chart",
            "price": price,
            "timestamp": now_utc(),
            "source_type": "external",
            "quality": "public_quote"
        }
    except Exception as e:
        return {
            "source": "yahoo_chart",
            "price": None,
            "source_type": "external",
            "quality": "failed",
            "error": str(e)
        }


def source_stooq(ticker):
    try:
        symbol = ticker.lower() + ".us"
        url = f"https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"
        text = fetch_text(url)

        lines = [x.strip() for x in text.splitlines() if x.strip()]
        if len(lines) < 2:
            return {
                "source": "stooq_csv",
                "price": None,
                "source_type": "external",
                "quality": "failed",
                "error": "No CSV data"
            }

        reader = csv.DictReader(lines)
        row = next(reader, None)
        if not row:
            return {
                "source": "stooq_csv",
                "price": None,
                "source_type": "external",
                "quality": "failed",
                "error": "No CSV row"
            }

        price = safe_float(row.get("Close"))

        return {
            "source": "stooq_csv",
            "price": price,
            "timestamp": f"{row.get('Date', '')} {row.get('Time', '')}".strip(),
            "source_type": "external",
            "quality": "public_quote"
        }
    except Exception as e:
        return {
            "source": "stooq_csv",
            "price": None,
            "source_type": "external",
            "quality": "failed",
            "error": str(e)
        }


def validate_price(ticker, external_sources, manual_inputs, tolerance_pct=1.00):
    valid_external = [
        s for s in external_sources
        if safe_float(s.get("price")) is not None
    ]

    manual_prices = [
        safe_float(s.get("price"))
        for s in manual_inputs
        if safe_float(s.get("price")) is not None
    ]

    if not valid_external:
        return {
            "ticker": ticker,
            "verified": False,
            "status": "no_external_price",
            "selected_price": None,
            "read": "No external price source returned a usable quote. Manual price is not enough for verification.",
            "external_sources": external_sources,
            "manual_inputs": manual_inputs,
            "next_action": "Refresh price sources or manually confirm price before replay."
        }

    external_prices = [safe_float(s.get("price")) for s in valid_external]
    external_prices_sorted = sorted(external_prices)
    median_external = external_prices_sorted[len(external_prices_sorted) // 2]

    close_external = []
    disagree_external = []

    for source in valid_external:
        price = safe_float(source.get("price"))
        diff_pct = abs((price - median_external) / median_external) * 100 if median_external else 999
        enriched = dict(source)
        enriched["diff_vs_external_median_pct"] = round(diff_pct, 3)

        if diff_pct <= tolerance_pct:
            close_external.append(enriched)
        else:
            disagree_external.append(enriched)

    manual_disagreement = False
    manual_diff_pct = None

    if manual_prices:
        latest_manual = manual_prices[-1]
        manual_diff_pct = abs((latest_manual - median_external) / median_external) * 100 if median_external else None
        if manual_diff_pct is not None and manual_diff_pct > tolerance_pct:
            manual_disagreement = True

    if len(close_external) >= 2:
        selected = round(sum(safe_float(s.get("price")) for s in close_external) / len(close_external), 4)

        if manual_disagreement:
            read = "External prices agree, but manual/batch price disagrees. External verified price should replace stale manual value."
            status = "verified_external_manual_disagreement"
        else:
            read = f"{len(close_external)} external sources agree within {tolerance_pct}%."
            status = "verified_external"

        return {
            "ticker": ticker,
            "verified": True,
            "status": status,
            "selected_price": selected,
            "read": read,
            "external_sources": close_external,
            "external_outliers": disagree_external,
            "manual_inputs": manual_inputs,
            "manual_diff_vs_external_pct": round(manual_diff_pct, 3) if manual_diff_pct is not None else None,
            "next_action": "Use verified external price."
        }

    if len(valid_external) == 1:
        source = valid_external[0]
        read = "Only one external source returned a usable quote. Do not treat as fully verified."
        if manual_disagreement:
            read += " Manual/batch price disagrees with the external quote."

        return {
            "ticker": ticker,
            "verified": False,
            "status": "single_external_source_warning",
            "selected_price": safe_float(source.get("price")),
            "read": read,
            "external_sources": valid_external,
            "manual_inputs": manual_inputs,
            "manual_diff_vs_external_pct": round(manual_diff_pct, 3) if manual_diff_pct is not None else None,
            "next_action": "Review price before replay or add another source."
        }

    return {
        "ticker": ticker,
        "verified": False,
        "status": "external_source_disagreement",
        "selected_price": median_external,
        "read": "External sources disagree beyond tolerance. Replay price should not be updated automatically.",
        "external_sources": valid_external,
        "external_outliers": disagree_external,
        "manual_inputs": manual_inputs,
        "manual_diff_vs_external_pct": round(manual_diff_pct, 3) if manual_diff_pct is not None else None,
        "next_action": "Review source prices before replay."
    }


def update_portfolio(results):
    portfolio = load_json(PORTFOLIO_SNAPSHOT, {})
    portfolio.setdefault("positions", {})

    updated = []

    for item in results:
        if not item.get("verified"):
            continue

        ticker = item.get("ticker")
        price = safe_float(item.get("selected_price"))

        if not ticker or price is None:
            continue

        old = portfolio["positions"].get(ticker, {})

        portfolio["positions"][ticker] = {
            "ticker": ticker,
            "quantity": old.get("quantity", 0),
            "average_cost": old.get("average_cost", 0),
            "current_price": price,
            "market_value": old.get("market_value", 0),
            "unrealized_pnl": old.get("unrealized_pnl", 0),
            "notes": "Updated by external-source price verification engine",
            "updated_at": now_utc(),
            "advisory_only": True
        }

        updated.append(ticker)

    portfolio["updated_at"] = now_utc()
    portfolio["source"] = "price_fallback_engine_external_verified"
    portfolio["advisory_only"] = True

    save_json(PORTFOLIO_SNAPSHOT, portfolio)

    return updated


def main():
    tickers = get_target_tickers()
    results = []

    for ticker in tickers:
        external = [
            source_yahoo(ticker),
            source_stooq(ticker),
        ]

        manual = manual_sources(ticker)

        results.append(validate_price(ticker, external, manual))

    updated = update_portfolio(results)

    payload = {
        "timestamp": now_utc(),
        "target_tickers": tickers,
        "updated_portfolio_tickers": updated,
        "results": results,
        "rule": {
            "manual_batch_prices_are_verification_sources": False,
            "portfolio_snapshot_prices_are_verification_sources": False,
            "verified_requires": "At least 2 external usable sources agreeing within tolerance.",
            "tolerance_pct": 1.00,
            "portfolio_update_policy": "external_verified_only"
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Price Verification Snapshot")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append("## Rule")
    lines.append("- Manual/batch prices are not verification sources.")
    lines.append("- Portfolio snapshot prices are not verification sources.")
    lines.append("- Verified price requires at least 2 external sources agreeing within tolerance.")
    lines.append("")
    lines.append("## Results")

    for item in results:
        lines.append("")
        lines.append(f"### {item.get('ticker')}")
        lines.append(f"- Status: {item.get('status')}")
        lines.append(f"- Verified: {item.get('verified')}")
        lines.append(f"- Selected price: {item.get('selected_price')}")
        lines.append(f"- Read: {item.get('read')}")
        lines.append(f"- Next action: {item.get('next_action')}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "tickers": tickers,
        "updated_portfolio_tickers": updated,
        "json": str(OUT_JSON),
        "report": str(OUT_MD)
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
