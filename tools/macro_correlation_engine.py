import json
from pathlib import Path
from datetime import datetime, timezone
import math

BASE = Path(__file__).resolve().parents[1]
OUT_JSON = BASE / "features" / "latest_macro_correlation_analysis.json"
OUT_MD = BASE / "reports" / "macro" / "latest_macro_correlation_analysis.md"
DATA_DIR = BASE / "data" / "market_history"

ASSETS = {
    "SPY": "US large-cap equities",
    "QQQ": "US growth / Nasdaq",
    "IWM": "US small caps",
    "DIA": "Dow industrials",
    "TLT": "long-duration bonds",
    "HYG": "high-yield credit",
    "LQD": "investment-grade credit",
    "GLD": "gold",
    "SLV": "silver",
    "USO": "oil proxy",
    "UUP": "US dollar proxy",
    "BTC-USD": "bitcoin / crypto risk"
}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def safe_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return default

def load_csv_prices(ticker):
    """
    Optional fallback:
    data/market_history/TICKER.csv with columns date,close
    """
    path = DATA_DIR / f"{ticker}.csv"
    if not path.exists():
        return []

    rows = []
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split(",")
        if len(parts) >= 2:
            close = safe_float(parts[1])
            if close is not None:
                rows.append(close)
    return rows

def try_yfinance_prices(ticker, period="6mo"):
    try:
        import yfinance as yf
        data = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if data is None or data.empty:
            return []
        closes = data["Close"].dropna().tolist()
        return [float(x) for x in closes]
    except Exception:
        return []

def pct_returns(prices):
    out = []
    for i in range(1, len(prices)):
        if prices[i-1] != 0:
            out.append((prices[i] - prices[i-1]) / prices[i-1])
    return out

def corr(a, b):
    n = min(len(a), len(b))
    if n < 10:
        return None

    a = a[-n:]
    b = b[-n:]

    ma = sum(a) / n
    mb = sum(b) / n

    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)

    if va == 0 or vb == 0:
        return None

    return cov / math.sqrt(va * vb)

def change(prices, n):
    if len(prices) <= n or prices[-n] == 0:
        return None
    return (prices[-1] - prices[-n]) / prices[-n]

def analyze_asset(prices):
    return {
        "last": prices[-1] if prices else None,
        "change_5d": change(prices, 5),
        "change_20d": change(prices, 20),
        "change_60d": change(prices, 60),
        "available_points": len(prices)
    }

def determine_macro_read(asset_stats, correlation):
    spy20 = asset_stats.get("SPY", {}).get("change_20d")
    qqq20 = asset_stats.get("QQQ", {}).get("change_20d")
    tlt20 = asset_stats.get("TLT", {}).get("change_20d")
    gld20 = asset_stats.get("GLD", {}).get("change_20d")
    uso20 = asset_stats.get("USO", {}).get("change_20d")
    uup20 = asset_stats.get("UUP", {}).get("change_20d")

    flags = []
    read = "mixed"

    if spy20 is not None and qqq20 is not None and spy20 > 0 and qqq20 > 0:
        flags.append("equities_positive")
        read = "risk_on_or_growth_supportive"

    if tlt20 is not None and tlt20 < 0:
        flags.append("bonds_weak_rates_pressure")

    if uup20 is not None and uup20 > 0:
        flags.append("dollar_strength_tightening_pressure")

    if uso20 is not None and uso20 > 0.08:
        flags.append("oil_inflation_pressure")

    if gld20 is not None and gld20 > 0 and spy20 is not None and spy20 > 0:
        flags.append("gold_and_equities_both_up_liquidity_or_uncertainty_mix")

    qualitative_followup = False
    followup_reasons = []

    if "dollar_strength_tightening_pressure" in flags and "equities_positive" in flags:
        qualitative_followup = True
        followup_reasons.append("Equities rising despite dollar strength. Need qualitative explanation.")

    if "oil_inflation_pressure" in flags:
        qualitative_followup = True
        followup_reasons.append("Oil strength may affect inflation/Fed/policy expectations.")

    if "gold_and_equities_both_up_liquidity_or_uncertainty_mix" in flags:
        qualitative_followup = True
        followup_reasons.append("Gold and equities rising together needs narrative check.")

    return {
        "macro_read": read,
        "flags": flags,
        "qualitative_followup_required": qualitative_followup,
        "qualitative_followup_reasons": followup_reasons
    }

def main():
    prices = {}
    returns = {}
    asset_stats = {}

    for ticker in ASSETS:
        p = try_yfinance_prices(ticker)
        if not p:
            p = load_csv_prices(ticker)

        prices[ticker] = p
        returns[ticker] = pct_returns(p)
        asset_stats[ticker] = analyze_asset(p)

    correlation = {}

    for a in ASSETS:
        correlation[a] = {}
        for b in ASSETS:
            correlation[a][b] = corr(returns[a], returns[b])

    macro = determine_macro_read(asset_stats, correlation)

    payload = {
        "timestamp": utc_now(),
        "assets": ASSETS,
        "asset_stats": asset_stats,
        "correlation": correlation,
        "macro_interpretation": macro
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Macro Correlation Analysis")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append("## Macro Read")
    lines.append("")
    lines.append(f"- Macro read: {macro['macro_read']}")
    lines.append(f"- Qualitative follow-up required: {macro['qualitative_followup_required']}")

    for r in macro["qualitative_followup_reasons"]:
        lines.append(f"- Follow-up reason: {r}")

    lines.append("")
    lines.append("## Major Asset Snapshot")
    lines.append("")
    for ticker, stats in asset_stats.items():
        lines.append(f"### {ticker} — {ASSETS[ticker]}")
        lines.append(f"- 5d: {stats.get('change_5d')}")
        lines.append(f"- 20d: {stats.get('change_20d')}")
        lines.append(f"- 60d: {stats.get('change_60d')}")
        lines.append(f"- Points: {stats.get('available_points')}")
        lines.append("")

    lines.append("## Correlation Matrix")
    lines.append("")
    header = "| Asset | " + " | ".join(ASSETS.keys()) + " |"
    sep = "|---|" + "|".join(["---:" for _ in ASSETS]) + "|"
    lines.append(header)
    lines.append(sep)

    for a in ASSETS:
        row = [a]
        for b in ASSETS:
            val = correlation[a][b]
            row.append("" if val is None else f"{val:.2f}")
        lines.append("| " + " | ".join(row) + " |")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "json": str(OUT_JSON),
        "report": str(OUT_MD),
        "qualitative_followup_required": macro["qualitative_followup_required"]
    }, indent=2))

if __name__ == "__main__":
    main()
