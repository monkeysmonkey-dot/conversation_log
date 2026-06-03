import csv
import json
import math
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

WATCHLIST = BASE / "data" / "sector_etf_watchlist.json"
MANUAL_OPTIONS = BASE / "data" / "manual_options_flow.csv"

OUT_JSON = BASE / "features" / "latest_sector_etf_flow.json"
OUT_MD = BASE / "reports" / "daily" / "latest_sector_etf_flow.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_float(value):
    try:
        if value in [None, ""]:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def pct_change(values, lookback):
    try:
        if len(values) <= lookback:
            return None
        old = float(values[-1 - lookback])
        new = float(values[-1])
        if old == 0:
            return None
        return ((new - old) / old) * 100.0
    except Exception:
        return None


def fmt_pct(value):
    if value is None:
        return ""
    try:
        return f"{value:+.2f}%"
    except Exception:
        return ""


def read_manual_options():
    if not MANUAL_OPTIONS.exists():
        return []

    rows = []
    try:
        with MANUAL_OPTIONS.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception:
        pass

    return rows


def analyze_manual_options():
    rows = read_manual_options()

    by_theme = {}
    by_sector = {}

    for row in rows:
        theme = row.get("theme", "") or "Unknown"
        sector = row.get("sector", "") or "Unknown"

        call_premium = safe_float(row.get("call_premium"))
        put_premium = safe_float(row.get("put_premium"))
        call_volume = safe_float(row.get("call_volume"))
        put_volume = safe_float(row.get("put_volume"))

        for bucket, key in [(by_theme, theme), (by_sector, sector)]:
            bucket.setdefault(key, {
                "call_premium": 0.0,
                "put_premium": 0.0,
                "call_volume": 0.0,
                "put_volume": 0.0,
                "rows": 0
            })

            bucket[key]["call_premium"] += call_premium
            bucket[key]["put_premium"] += put_premium
            bucket[key]["call_volume"] += call_volume
            bucket[key]["put_volume"] += put_volume
            bucket[key]["rows"] += 1

    def finalize(bucket):
        out = []
        for key, item in bucket.items():
            call_premium = item["call_premium"]
            put_premium = item["put_premium"]
            call_volume = item["call_volume"]
            put_volume = item["put_volume"]

            total_premium = call_premium + put_premium
            total_volume = call_volume + put_volume

            call_share = (call_premium / total_premium) * 100 if total_premium > 0 else 0
            put_share = (put_premium / total_premium) * 100 if total_premium > 0 else 0

            if total_premium <= 0 and total_volume > 0:
                call_share = (call_volume / total_volume) * 100
                put_share = (put_volume / total_volume) * 100

            if call_share >= 65:
                read = "bullish_options_pressure"
            elif put_share >= 65:
                read = "bearish_options_pressure"
            elif total_premium > 0 or total_volume > 0:
                read = "mixed_options_pressure"
            else:
                read = "no_manual_options_data"

            out.append({
                "key": key,
                "rows": item["rows"],
                "call_premium": round(call_premium, 2),
                "put_premium": round(put_premium, 2),
                "call_volume": round(call_volume, 2),
                "put_volume": round(put_volume, 2),
                "call_share": round(call_share, 2),
                "put_share": round(put_share, 2),
                "read": read
            })

        return sorted(out, key=lambda x: (x["call_premium"] + x["put_premium"] + x["call_volume"] + x["put_volume"]), reverse=True)

    return {
        "manual_rows": len(rows),
        "by_theme": finalize(by_theme),
        "by_sector": finalize(by_sector)
    }


def fetch_prices(symbols):
    try:
        import yfinance as yf
    except Exception:
        return {}, "yfinance_missing"

    data = {}

    try:
        hist = yf.download(
            tickers=" ".join(symbols),
            period="90d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True
        )

        for symbol in symbols:
            try:
                if len(symbols) == 1:
                    close = hist["Close"].dropna().tolist()
                    volume = hist["Volume"].dropna().tolist()
                else:
                    close = hist[(symbol, "Close")].dropna().tolist()
                    volume = hist[(symbol, "Volume")].dropna().tolist()

                if close:
                    data[symbol] = {
                        "close": [float(x) for x in close],
                        "volume": [float(x) for x in volume]
                    }
            except Exception:
                continue

        return data, "yfinance"

    except Exception as e:
        return {}, f"price_fetch_error: {e}"


def score_etf(symbol, meta, series, spy_returns, qqq_returns):
    closes = series.get("close", [])
    volumes = series.get("volume", [])

    r1 = pct_change(closes, 1)
    r5 = pct_change(closes, 5)
    r20 = pct_change(closes, 20)

    spy5 = spy_returns.get("5d")
    qqq5 = qqq_returns.get("5d")

    rs_spy_5d = r5 - spy5 if r5 is not None and spy5 is not None else None
    rs_qqq_5d = r5 - qqq5 if r5 is not None and qqq5 is not None else None

    volume_ratio = None
    if len(volumes) >= 21:
        avg20 = sum(volumes[-21:-1]) / 20.0
        if avg20 > 0:
            volume_ratio = volumes[-1] / avg20

    score = 0

    for value, weight in [(r1, 1), (r5, 2), (r20, 2), (rs_spy_5d, 2), (rs_qqq_5d, 1)]:
        if value is not None:
            if value > 0:
                score += weight
            elif value < 0:
                score -= weight

    if volume_ratio is not None:
        if volume_ratio >= 1.5:
            score += 2
        elif volume_ratio >= 1.15:
            score += 1
        elif volume_ratio <= 0.75:
            score -= 1

    if score >= 6:
        flow_read = "strong_inflow_momentum"
    elif score >= 3:
        flow_read = "positive_momentum"
    elif score <= -5:
        flow_read = "strong_outflow_or_weakness"
    elif score <= -2:
        flow_read = "negative_momentum"
    else:
        flow_read = "mixed_or_neutral"

    return {
        "symbol": symbol,
        "name": meta.get("name", ""),
        "sector": meta.get("sector", ""),
        "region": meta.get("region", ""),
        "theme_links": meta.get("theme_links", []),
        "last_price": round(closes[-1], 4) if closes else None,
        "return_1d": r1,
        "return_5d": r5,
        "return_20d": r20,
        "rs_spy_5d": rs_spy_5d,
        "rs_qqq_5d": rs_qqq_5d,
        "volume_ratio": round(volume_ratio, 3) if volume_ratio is not None else None,
        "momentum_score": score,
        "flow_read": flow_read
    }


def main():
    watch = load_json(WATCHLIST, {"base_index": "SPY", "growth_index": "QQQ", "sector_etfs": []})

    etfs = watch.get("sector_etfs", [])
    base_index = watch.get("base_index", "SPY")
    growth_index = watch.get("growth_index", "QQQ")

    symbols = sorted(set([base_index, growth_index] + [x.get("symbol") for x in etfs if x.get("symbol")]))

    price_data, price_source = fetch_prices(symbols)

    spy_returns = {}
    qqq_returns = {}

    if base_index in price_data:
        spy_returns = {
            "5d": pct_change(price_data[base_index]["close"], 5)
        }

    if growth_index in price_data:
        qqq_returns = {
            "5d": pct_change(price_data[growth_index]["close"], 5)
        }

    etf_rows = []

    for meta in etfs:
        symbol = meta.get("symbol")
        if symbol in price_data:
            etf_rows.append(score_etf(symbol, meta, price_data[symbol], spy_returns, qqq_returns))
        else:
            etf_rows.append({
                "symbol": symbol,
                "name": meta.get("name", ""),
                "sector": meta.get("sector", ""),
                "region": meta.get("region", ""),
                "theme_links": meta.get("theme_links", []),
                "last_price": None,
                "return_1d": None,
                "return_5d": None,
                "return_20d": None,
                "rs_spy_5d": None,
                "rs_qqq_5d": None,
                "volume_ratio": None,
                "momentum_score": 0,
                "flow_read": "price_data_missing"
            })

    etf_rows = sorted(etf_rows, key=lambda x: x.get("momentum_score", 0), reverse=True)

    options = analyze_manual_options()

    theme_scores = {}

    for row in etf_rows:
        for theme in row.get("theme_links", []):
            theme_scores.setdefault(theme, {
                "theme": theme,
                "etfs": 0,
                "score_total": 0.0,
                "positive": 0,
                "negative": 0,
                "leaders": []
            })

            theme_scores[theme]["etfs"] += 1
            theme_scores[theme]["score_total"] += safe_float(row.get("momentum_score"))
            theme_scores[theme]["leaders"].append({
                "symbol": row.get("symbol"),
                "score": row.get("momentum_score"),
                "flow_read": row.get("flow_read")
            })

            if row.get("momentum_score", 0) > 0:
                theme_scores[theme]["positive"] += 1
            elif row.get("momentum_score", 0) < 0:
                theme_scores[theme]["negative"] += 1

    theme_rows = []

    for theme, item in theme_scores.items():
        avg_score = item["score_total"] / item["etfs"] if item["etfs"] else 0

        if avg_score >= 4:
            read = "theme_money_flow_strong"
        elif avg_score >= 2:
            read = "theme_money_flow_positive"
        elif avg_score <= -3:
            read = "theme_money_flow_weak"
        else:
            read = "theme_money_flow_mixed"

        leaders = sorted(item["leaders"], key=lambda x: x.get("score", 0), reverse=True)[:5]

        theme_rows.append({
            "theme": theme,
            "etfs": item["etfs"],
            "average_score": round(avg_score, 2),
            "positive_etfs": item["positive"],
            "negative_etfs": item["negative"],
            "read": read,
            "leaders": leaders
        })

    theme_rows = sorted(theme_rows, key=lambda x: x["average_score"], reverse=True)

    payload = {
        "timestamp": now_utc(),
        "price_source": price_source,
        "base_index": base_index,
        "growth_index": growth_index,
        "etf_rows": etf_rows,
        "theme_rows": theme_rows,
        "manual_options_flow": options,
        "method": {
            "momentum_score": "Combines ETF returns, relative strength vs SPY/QQQ, and volume participation.",
            "options_flow": "Uses manual options flow CSV until a paid or approved options-flow source is integrated.",
            "advisory_only": True
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Sector / ETF / Options Flow")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Price source: {price_source}")
    lines.append("")
    lines.append("## Top ETF Flow Reads")
    for row in etf_rows[:12]:
        lines.append(
            f"- {row.get('symbol')} | {row.get('sector')} | score {row.get('momentum_score')} | "
            f"5D {fmt_pct(row.get('return_5d'))} | RS SPY {fmt_pct(row.get('rs_spy_5d'))} | {row.get('flow_read')}"
        )

    lines.append("")
    lines.append("## Theme Money Flow")
    for row in theme_rows[:12]:
        lines.append(f"- {row.get('theme')}: {row.get('read')} | avg score {row.get('average_score')}")

    lines.append("")
    lines.append("## Manual Options Flow")
    lines.append(f"- Rows: {options.get('manual_rows', 0)}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "price_source": price_source,
        "etfs": len(etf_rows),
        "themes": len(theme_rows),
        "manual_options_rows": options.get("manual_rows", 0),
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
