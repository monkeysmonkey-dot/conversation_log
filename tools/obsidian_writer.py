from pathlib import Path
from datetime import datetime, timezone
import re

BASE = Path(__file__).resolve().parents[1]
VAULT = BASE / "obsidian_vault"

def safe_name(text):
    text = str(text)

    # Keep only safe filename characters.
    text = re.sub(r"[^A-Za-z0-9_. -]", "", text)

    # Normalize spaces.
    text = text.strip().replace(" ", "_")

    if not text:
        text = "untitled"

    return text[:80]

def write_note(folder, title, body):
    target = VAULT / folder
    target.mkdir(parents=True, exist_ok=True)

    filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{safe_name(title)}.md"
    path = target / filename

    path.write_text(str(body), encoding="utf-8")
    return str(path)

def write_daily_report(title, summary, payload_text):
    body = f"""# {title}

Created: {datetime.now(timezone.utc).isoformat()}

## Summary

{summary}

## Details

{payload_text}
"""
    return write_note("01_Daily_Reports", title, body)

def write_thesis(symbol, title, thesis, confidence):
    body = f"""# {symbol} — {title}

Created: {datetime.now(timezone.utc).isoformat()}

Status: active
Confidence: {confidence}

## Thesis

{thesis}

## Follow-Up

- Validate catalyst
- Track price reaction
- Review macro alignment
"""
    return write_note("03_Thesis", f"{symbol}_{title}", body)
