import os
import re
import shutil
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\Abe\hermes agent\project\stock manager")
BACKUP = BASE / ".backup"
RUN = BACKUP / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

RUN.mkdir(parents=True, exist_ok=True)

PATTERNS = [
    r"api[_-]?key",
    r"token",
    r"secret",
    r"password",
]

IGNORE = [".git", "__pycache__", ".backup"]

def is_sensitive(text):
    for p in PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

def sanitize(text):
    # Replace values with placeholder
    return re.sub(r"=(.*)", "=YOUR_VALUE_HERE", text)

def process_file(path):
    try:
        content = path.read_text(errors="ignore")
    except:
        return

    if not is_sensitive(content):
        return

    rel = path.relative_to(BASE)
    backup_path = RUN / rel
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(path, backup_path)

    path.write_text(sanitize(content), encoding="utf-8")

    print(f"[SANITIZED] {rel}")

def main():
    for root, dirs, files in os.walk(BASE):
        if any(i in root for i in IGNORE):
            continue

        for f in files:
            process_file(Path(root) / f)

    print(f"✅ Backup created: {RUN}")

if __name__ == "__main__":
    main()
