import os
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def clean_error(e):
    msg =YOUR_VALUE_HERE
    if "apikey=YOUR_VALUE_HERE
        msg =YOUR_VALUE_HERE
    return msg

def run(symbols=YOUR_VALUE_HERE
    symbols =YOUR_VALUE_HERE
    api_key =YOUR_VALUE_HERE

    if not api_key:
        return {
            "provider": "alphavantage",
            "status": "missing_api_key",
            "news_sentiment": {},
            "company_overview": {},
            "note": "Alpha Vantage key missing. Used for news sentiment/company overview, not transcripts.",
            "timestamp": utc_now()
        }

    news_results =YOUR_VALUE_HERE
    overview_results =YOUR_VALUE_HERE

    # Alpha Vantage free tier can be rate limited, so start with fewer symbols.
    limited_symbols =YOUR_VALUE_HERE

    for symbol in limited_symbols:
        try:
            url =YOUR_VALUE_HERE
            params =YOUR_VALUE_HERE
                "function": "NEWS_SENTIMENT",
                "tickers": symbol,
                "limit": 10,
                "apikey": api_key
            }

            r =YOUR_VALUE_HERE
            r.raise_for_status()
            data =YOUR_VALUE_HERE

            news_results[symbol] =YOUR_VALUE_HERE
                "status": "ok",
                "data": data
            }

        except Exception as e:
            news_results[symbol] =YOUR_VALUE_HERE
                "status": "error",
                "error": clean_error(e)
            }

        time.sleep(1)

        try:
            url =YOUR_VALUE_HERE
            params =YOUR_VALUE_HERE
                "function": "OVERVIEW",
                "symbol": symbol,
                "apikey": api_key
            }

            r =YOUR_VALUE_HERE
            r.raise_for_status()
            data =YOUR_VALUE_HERE

            overview_results[symbol] =YOUR_VALUE_HERE
                "status": "ok",
                "data": data
            }

        except Exception as e:
            overview_results[symbol] =YOUR_VALUE_HERE
                "status": "error",
                "error": clean_error(e)
            }

        time.sleep(1)

    return {
        "provider": "alphavantage",
        "status": "ok",
        "news_sentiment": news_results,
        "company_overview": overview_results,
        "note": "Alpha Vantage is used for news sentiment/company overview/fundamental context, not earnings transcripts.",
        "timestamp": utc_now()
    }

if __name__ =YOUR_VALUE_HERE
    import json
    print(json.dumps(run(), indent=YOUR_VALUE_HERE
