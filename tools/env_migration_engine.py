import re
import shutil
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\Abe\hermes agent\project\stock manager")

ENV_FILE = BASE / ".env"
BACKUP_DIR = BASE / f".env_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

BACKUP_DIR.mkdir(exist_ok=True)

# Patterns to detect secrets
PATTERNS = [
    r"(api_key\s*=\s*[\"'].*?[\"'])",
    r"(token\s*=\s*[\"'].*?[\"'])",
    r"(refresh_token\s*=\s*[\"'].*?[\"'])",
    r"([REDACTED][A-Za-z0-9\-._~+/]+=*)",
    r"(sk-[A-Za-z0-9]+)"
]

found_env = {}

def extract_secret(line):
    for p in PATTERNS:
        m = re.search(p, line, re.IGNORECASE)
        if m:
            return m.group(0)
    return None

def sanitize_and_extract(path):
    try:
        content = path.read_text(errors="ignore")
    except:
        return

    lines = content.splitlines()
    new_lines = []
    modified = False

    for line in lines:
        secret = extract_secret(line)

        if secret:
            key_name = None
            value = None

            if "=" in secret:
                parts = secret.split("=", 1)
                key_name = parts[0].strip().upper()
                value = parts[1].strip().strip("'\"")

            elif "Bearer" in secret:
                key_name = "BEARER_TOKEN"
                value = secret.replace("Bearer", "").strip()

            elif "sk-" in secret:
                key_name = "API_KEY"
                value = secret.strip()

            if key_name and value:
                key_name = re.sub(r"[^A-Z0-9_]", "_", key_name)

                found_env[key_name] = value

                # replace code line
                new_line = f'{key_name} = os.getenv("{key_name}")'
                new_lines.append("import os")
                new_lines.append(new_line)

                modified = True
                continue

        new_lines.append(line)

    if modified:
        rel = path.relative_to(BASE)
        backup_path = BACKUP_DIR / rel
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(path, backup_path)

        path.write_text("\n".join(new_lines), encoding="utf-8")

        print(f"[UPDATED] {rel}")

def scan():
    for f in BASE.rglob("*.py"):
        if any(x in str(f) for x in [".git", "__pycache__", ".backup", "backup"]):
            continue
        sanitize_and_extract(f)

def write_env():
    if not found_env:
        print("✅ No secrets extracted")
        return

    lines = []
    for k, v in found_env.items():
        lines.append(f"{k}={v}")

    ENV_FILE.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ .env created with {len(found_env)} entries")

def main():
    print("🔍 Scanning project for secrets...")
    scan()
    write_env()
    print(f"✅ Backup stored in {BACKUP_DIR}")

if __name__ == "__main__":
    main()
