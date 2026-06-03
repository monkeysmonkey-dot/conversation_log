import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

FRED_SERIES =YOUR_VALUE_HERE
    "fed_funds": "FEDFUNDS",
    "cpi": "CPIAUCSL",
    "unemployment": "UNRATE",
    "gdp": "GDP",
    "10y_minus_2y": "T10Y2Y",
    "financial_conditions": "NFCI"
}

def run():
    api_key =YOUR_VALUE_HERE

    if not api_key:
        return {
            "provider": "fred",
            "status": "missing_api_key",
            "series": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    results =YOUR_VALUE_HERE

    for name, series_id in FRED_SERIES.items():
        try:
            url =YOUR_VALUE_HERE
            params =YOUR_VALUE_HERE
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 5
            }

            r =YOUR_VALUE_HERE
            r.raise_for_status()
            data =YOUR_VALUE_HERE

            observations =YOUR_VALUE_HERE

            results[name] =YOUR_VALUE_HERE
                "series_id": series_id,
                "latest": observations[0] if observations else None,
                "recent": observations[:5]
            }

        except Exception as e:
            results[name] =YOUR_VALUE_HERE
                "series_id": series_id,
                "error": str(e)
            }

    return {
        "provider": "fred",
        "status": "ok",
        "series": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
