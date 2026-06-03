import yfinance as yf
import numpy as np
from datetime import datetime, timezone

DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "SPY", "QQQ"]

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

def run(symbols=None):
    symbols = symbols or DEFAULT_SYMBOLS
    results = {}
    spy_change = None

    for s in symbols:
        try:
            data = yf.download(
                s,
                period="65d",
                interval="1d",
                progress=False,
                auto_adjust=True,
                group_by="column"
            )

            if data is None or data.empty or len(data) < 20:
                results[s] = {"error": "insufficient_price_data"}
                continue

            close_series = data["Close"]
            volume_series = data["Volume"]

            close = scalar(close_series.iloc[-1])
            prev_5 = scalar(close_series.iloc[-5])
            prev_20 = scalar(close_series.iloc[-20])
            prev_60 = scalar(close_series.iloc[-60]) if len(data) >= 60 else prev_20

            volume = int(scalar(volume_series.iloc[-1], 0))
            avg_volume = scalar(volume_series.tail(20).mean(), 1)

            returns = close_series.pct_change().dropna()
            volatility = scalar(np.std(returns.tail(20)), 0.0)

            change_5d = (close - prev_5) / prev_5 if prev_5 else 0
            change_20d = (close - prev_20) / prev_20 if prev_20 else 0
            change_60d = (close - prev_60) / prev_60 if prev_60 else 0

            if s == "SPY":
                spy_change = change_20d

            results[s] = {
                "price": close,
                "change_5d": change_5d,
                "change_20d": change_20d,
                "change_60d": change_60d,
                "volume": volume,
                "avg_volume_20d": avg_volume,
                "volume_ratio": volume / avg_volume if avg_volume else 0,
                "volatility_20d": volatility,
                "trend_score": change_20d / (volatility + 1e-6),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            results[s] = {"error": str(e)}

    if spy_change is not None:
        for s, row in results.items():
            if isinstance(row, dict) and "change_20d" in row:
                row["relative_strength_vs_spy"] = row["change_20d"] - spy_change

    return results
