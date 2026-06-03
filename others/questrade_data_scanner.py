import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def run():
    refresh_token =YOUR_VALUE_HERE
    data_only =YOUR_VALUE_HERE
    trading_enabled =YOUR_VALUE_HERE

    if trading_enabled:
        return {
            "provider": "questrade",
            "status": "blocked",
            "reason": "QUESTRADE_TRADING_ENABLED must remain false. This system is data-collection only.",
            "timestamp": utc_now()
        }

    if not data_only:
        return {
            "provider": "questrade",
            "status": "blocked",
            "reason": "QUESTRADE_DATA_ONLY must remain true.",
            "timestamp": utc_now()
        }

    if not refresh_token:
        return {
            "provider": "questrade",
            "status": "missing_refresh_token",
            "data_only": True,
            "trading_enabled": False,
            "allowed_actions": [
                "account snapshot",
                "balances",
                "positions",
                "activity",
                "quotes"
            ],
            "blocked_actions": [
                "place_order",
                "modify_order",
                "cancel_order"
            ],
            "timestamp": utc_now()
        }

    # Safe placeholder.
    # Next step is to implement token refresh and data GET endpoints only.
    return {
        "provider": "questrade",
        "status": "configured_not_yet_wired",
        "data_only": True,
        "trading_enabled": False,
        "note": "Refresh token detected. Scanner will only be wired for GET/account/portfolio/quote data. No order endpoints allowed.",
        "allowed_actions": [
            "get_accounts",
            "get_balances",
            "get_positions",
            "get_activity",
            "get_quotes"
        ],
        "blocked_actions": [
            "place_order",
            "modify_order",
            "cancel_order",
            "live_trading"
        ],
        "timestamp": utc_now()
    }

def place_order(*args, **kwargs):
    raise RuntimeError("Blocked: Questrade trading/order placement is disabled. Data collection only.")

def modify_order(*args, **kwargs):
    raise RuntimeError("Blocked: Questrade order modification is disabled. Data collection only.")

def cancel_order(*args, **kwargs):
    raise RuntimeError("Blocked: Questrade order cancellation is disabled. Data collection only.")

if __name__ =YOUR_VALUE_HERE
    print(json.dumps(run(), indent=YOUR_VALUE_HERE
