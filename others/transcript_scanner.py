import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

def run(symbols=YOUR_VALUE_HERE
    symbols =YOUR_VALUE_HERE
    fmp_key =YOUR_VALUE_HERE

    if not fmp_key:
        return {
            "provider": "fmp",
            "status": "missing_api_key",
            "transcripts": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    results =YOUR_VALUE_HERE

    for symbol in symbols:
        try:
            # Placeholder: latest transcript endpoint can be expanded later.
            # Specific transcript endpoint requires quarter/year.
            url =YOUR_VALUE_HERE
            params =YOUR_VALUE_HERE
                "quarter": 1,
                "year": 2026,
                "apikey": fmp_key
            }

            r =YOUR_VALUE_HERE
            r.raise_for_status()

            data =YOUR_VALUE_HERE

            results[symbol] =YOUR_VALUE_HERE
                "items": data[:1] if isinstance(data, list) else data
            }

        except Exception as e:
            results[symbol] =YOUR_VALUE_HERE

    return {
        "provider": "fmp",
        "status": "ok",
        "transcripts": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
