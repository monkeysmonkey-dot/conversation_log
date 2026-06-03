import os
import re
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def clean_error(e):
    msg =YOUR_VALUE_HERE
    msg =YOUR_VALUE_HERE
    msg =YOUR_VALUE_HERE
    return msg

def run(symbols=YOUR_VALUE_HERE
    symbols =YOUR_VALUE_HERE
    finnhub_key =YOUR_VALUE_HERE

    if not finnhub_key:
        return {
            "provider": "finnhub",
            "status": "missing_api_key",
            "press_releases": {},
            "timestamp": utc_now()
        }

    today =YOUR_VALUE_HERE
    from_date =YOUR_VALUE_HERE
    to_date =YOUR_VALUE_HERE

    results =YOUR_VALUE_HERE

    for symbol in symbols:
        try:
            url =YOUR_VALUE_HERE
            params =YOUR_VALUE_HERE
                "symbol": symbol,
                "from": from_date,
                "to": to_date,
                "token": finnhub_key
            }

            r =YOUR_VALUE_HERE

            if r.status_code =YOUR_VALUE_HERE
                results[symbol] =YOUR_VALUE_HERE
                    "status": "forbidden",
                    "note": "Finnhub returned 403. Endpoint may require paid plan or enabled permission.",
                    "from": from_date,
                    "to": to_date
                }
                continue

            if r.status_code =YOUR_VALUE_HERE
                results[symbol] =YOUR_VALUE_HERE
                    "status": "rate_limited",
                    "note": "Finnhub returned 429.",
                    "from": from_date,
                    "to": to_date
                }
                continue

            r.raise_for_status()

            results[symbol] =YOUR_VALUE_HERE
                "status": "ok",
                "from": from_date,
                "to": to_date,
                "data": r.json()
            }

        except Exception as e:
            results[symbol] =YOUR_VALUE_HERE
                "status": "error",
                "error": clean_error(e),
                "from": from_date,
                "to": to_date
            }

    return {
        "provider": "finnhub",
        "status": "ok",
        "press_releases": results,
        "timestamp": utc_now()
    }

if __name__ =YOUR_VALUE_HERE
    import json
    print(json.dumps(run(), indent=YOUR_VALUE_HERE
