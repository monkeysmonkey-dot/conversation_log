import sys
import os
import json
import time
from datetime import datetime, timezone

sys.path.append(os.path.dirname(__file__))

from price_scanner import run as price_run
from macro_scanner import run as macro_run
from flow_scanner import run as flow_run
from sentiment_scanner import run as sentiment_run
from news_scanner import run as news_run
from catalyst_scanner import run as catalyst_run
from event_scanner import run as event_run
from db import insert_tool_call

def retry(func, attempts=3, delay=1):
    last_error = None

    for _ in range(attempts):
        try:
            return func()
        except Exception as e:
            last_error = str(e)
            time.sleep(delay)

    return {"error": "retry_failed", "last_error": last_error}

def safe_run(run_id, name, func):
    result = retry(func)
    status = "error" if isinstance(result, dict) and "error" in result else "ok"

    try:
        insert_tool_call(run_id, name, status, result)
    except Exception:
        pass

    return result

def run_all(run_id="manual", symbols=None):
    started = datetime.now(timezone.utc)

    price = safe_run(run_id, "price_scanner", lambda: price_run(symbols))
    macro = safe_run(run_id, "macro_scanner", macro_run)
    flow = safe_run(run_id, "flow_scanner", flow_run)
    sentiment = safe_run(run_id, "sentiment_scanner", sentiment_run)
    news = safe_run(run_id, "news_scanner", lambda: news_run(symbols))
    catalysts = safe_run(run_id, "catalyst_scanner", lambda: catalyst_run(news))
    events = safe_run(run_id, "event_scanner", event_run)

    finished = datetime.now(timezone.utc)

    return {
        "timestamp": finished.isoformat(),
        "scanner_started": started.isoformat(),
        "scanner_finished": finished.isoformat(),
        "price": price,
        "macro": macro,
        "flow": flow,
        "sentiment": sentiment,
        "news": news,
        "catalysts": catalysts,
        "events": events
    }

if __name__ == "__main__":
    print(json.dumps(run_all(), ensure_ascii=False))
