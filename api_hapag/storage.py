"""
storage.py
Gerencia leitura e escrita de cookies e tokens.
"""

import json
from pathlib import Path

ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

COOKIES_FILE = ARTIFACTS_DIR / "cookies.json"
XTOKEN_FILE = ARTIFACTS_DIR / "xtoken.txt"


def save_cookies(cookies: list):
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)


def load_cookies() -> list | None:
    if COOKIES_FILE.exists():
        return json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
    return None


def save_token(token: str):
    XTOKEN_FILE.write_text(token, encoding="utf-8")


def load_token() -> str | None:
    if XTOKEN_FILE.exists():
        token = XTOKEN_FILE.read_text(encoding="utf-8").strip()
        if token.startswith("eyJ") and len(token) > 50:
            return token
    return None
