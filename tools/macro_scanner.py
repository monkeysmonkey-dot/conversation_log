import yfinance as yf
from datetime import datetime, timezone

MACRO_SYMBOLS = {
    "10y_yield": "^TNX",
    "oil": "CL=F",
    "spy": "SPY",
    "qqq": "QQQ",
    "gold": "GC=F",
    "vix": "^VIX"
}

def scalar(x, default=0.0):
    try:
        if hasattr(x, "iloc"):
            x = x.iloc[0]
        if hasattr(x, "item"):
            x = x.item()
        return float(x)
    except Exception:
        try:
            return float(x)
        except Exception:
            return default

def run():
    results = {}

    for name, ticker in MACRO_SYMBOLS.items():
        try:
            data = yf.download(
                ticker,
                period="30d",
                interval="1d",
                progress=False,
                auto_adjust=True,
                group_by="column"
            )

            if data is None or data.empty or len(data) < 10:
                results[name] = {"ticker": ticker, "error": "insufficient_macro_data"}
                continue

            close_series = data["Close"]

            last = scalar(close_series.iloc[-1])
            prev_5 = scalar(close_series.iloc[-5])
            prev_20 = scalar(close_series.iloc[-20]) if len(data) >= 20 else prev_5

            results[name] = {
                "ticker": ticker,
                "last": last,
                "change_5d": (last / prev_5 - 1) if prev_5 else 0,
                "change_20d": (last / prev_20 - 1) if prev_20 else 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            results[name] = {"ticker": ticker, "error": str(e)}

    return results
