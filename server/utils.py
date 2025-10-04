import os
import re
import time
import secrets
from typing import Dict, Optional


ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def nanoid(size: int = 10) -> str:
    return "".join(ALPHABET[secrets.randbelow(len(ALPHABET))] for _ in range(size))


def slugify_str(s: str) -> str:
    # emulate slugify strict+lower: keep [a-z0-9] and replace others with '-'
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def now_ms() -> int:
    return int(time.time() * 1000)


def from_env(v: Optional[str]) -> str:
    return (v or "").strip().lower()


def parse_bool(v: Optional[str], fallback: bool) -> bool:
    s = from_env(v)
    if s in {"1", "true", "yes", "on", "y"}:
        return True
    if s in {"0", "false", "no", "off", "n", ""}:
        return False
    return fallback


def cookie_kwargs() -> Dict:
    is_prod = os.getenv("NODE_ENV") == "production"
    https_enabled = parse_bool(os.getenv("HTTPS_ENABLED"), is_prod)
    same_site = "none" if https_enabled else "lax"
    return dict(
        httponly=True,
        samesite=same_site,
        secure=https_enabled,
        domain=os.getenv("COOKIE_DOMAIN") or None,
        path="/",
        max_age=7 * 24 * 60 * 60,
    )

