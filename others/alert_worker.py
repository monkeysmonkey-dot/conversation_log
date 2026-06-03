import os
import requests
from dotenv import load_dotenv

load_dotenv()

def send_telegram(message):
    token =YOUR_VALUE_HERE
    chat_id =YOUR_VALUE_HERE

    if not token or not chat_id:
        return {"sent": False, "reason": "telegram_not_configured"}

    url =YOUR_VALUE_HERE
    r =YOUR_VALUE_HERE

    return {"sent": r.ok, "status_code": r.status_code}

def dispatch_alert(message):
    return {"telegram": send_telegram(message)}
