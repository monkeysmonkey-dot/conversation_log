import sys
import os
import json
import argparse
from datetime import datetime, timezone

# Force UTF-8 stdout on Windows if possible
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(os.path.join(BASE, "tools"))
sys.path.append(os.path.join(BASE, "core"))

from source_router import get_sources_for

from gdelt_geo_scanner import run as gdelt_run
from sec_filing_scanner import run as sec_run
from fred_macro_scanner import run as fred_run
from news_scanner import run as financial_news_run
from alphavantage_qual_scanner import run as alphavantage_run
from transcript_scanner import run as transcript_run
from press_release_scanner import run as press_run

def source_status(category):
    return get_sources_for(category)

def safe_call(name, func):
    try:
        return func()
    except Exception as e:
        return {
            "provider": name,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

def run_all(symbols=None):
    symbols = symbols or ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]

    routing = {
        "macro_hard_data": source_status("macro_hard_data"),
        "macro_narrative": source_status("macro_narrative"),
        "geopolitical": source_status("geopolitical"),
        "filings": source_status("filings"),
        "transcripts": source_status("transcripts"),
        "press_releases": source_status("press_releases"),
        "sentiment": source_status("sentiment")
    }

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "routing": routing,

        "gdelt_geopolitical": safe_call("gdelt", gdelt_run),
        "sec_filings": safe_call("sec", lambda: sec_run(symbols)),
        "fred_macro": safe_call("fred", fred_run),
        "financial_news": safe_call("financial_news_api", lambda: financial_news_run(symbols)),
        "alphavantage": safe_call("alphavantage", lambda: alphavantage_run(symbols)),
        "transcripts": safe_call("transcripts", lambda: transcript_run(symbols)),
        "press_releases": safe_call("press_releases", lambda: press_run(symbols))
    }

    return payload

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="", help="Write JSON output to file using UTF-8")
    args = parser.parse_args()

    data = run_all()
    text = json.dumps(data, indent=2, ensure_ascii=False)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(json.dumps({
            "status": "written",
            "path": args.out,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, indent=2))
    else:
        print(text)

if __name__ == "__main__":
    main()
