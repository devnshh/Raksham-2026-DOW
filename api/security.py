"""
Shared secrets and API-key checks for SATARK.

Keys come from environment variables. Nothing is hard-coded: if a key is not set,
a random one is generated for this process and logged once, so a fresh checkout is
never protected by a well-known default.
"""

import logging
import os
import secrets
from typing import Dict, Optional

from fastapi import Header, HTTPException, status

logger = logging.getLogger("satark.security")

_generated: dict = {}


def secret_from_env(*names: str) -> str:
    """Returns the first set env var among `names`, else a per-process random key (logged once)."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    label = names[0]
    if label not in _generated:
        _generated[label] = secrets.token_urlsafe(24)
        logger.warning("%s is not set; generated a one-time key for this run: %s", label, _generated[label])
    return _generated[label]


def analyst_key() -> str:
    """Key for analyst and case endpoints (also accepted on /internal routes)."""
    return secret_from_env("SATARK_ANALYST_KEY", "INTERNAL_API_KEY", "SATARK_INTERNAL_KEY")


def analyst_keys() -> Dict[str, str]:
    """Per-analyst keys from SATARK_ANALYST_KEYS ("alice:key1,bob:key2"), as key -> analyst ID. Empty if unset."""
    pairs = [p.split(":", 1) for p in os.getenv("SATARK_ANALYST_KEYS", "").split(",") if ":" in p]
    return {key.strip(): name.strip().lower() for name, key in pairs if name.strip() and key.strip()}


def require_analyst_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[str]:
    """FastAPI dependency: accepts `X-API-Key: <key>` or `Authorization: Bearer <key>`.

    With per-analyst keys configured (SATARK_ANALYST_KEYS) it returns the analyst bound to the key and the
    shared key is refused, so "two distinct analysts" really means two people. With only the shared key
    (the demo) it returns None and the analyst ID typed in the request is used."""
    provided = x_api_key
    if not provided and authorization:
        provided = authorization[7:].strip() if authorization.lower().startswith("bearer ") else authorization.strip()
    if provided:
        given = provided.encode()  # bytes: compare_digest raises on non-ASCII str
        per_analyst = analyst_keys()
        if per_analyst:
            for key, name in per_analyst.items():
                if secrets.compare_digest(given, key.encode()):
                    return name
        elif secrets.compare_digest(given, analyst_key().encode()):
            return None
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: invalid or missing analyst API key",
    )


def acting_analyst(bound: Optional[str], claimed: Optional[str]) -> str:
    """Who is acting: the analyst bound to the key, else (shared demo key) the ID they typed. Never blank."""
    who = (bound or claimed or "").strip().lower()
    if not who:
        raise HTTPException(status_code=422, detail="analyst_id is required")
    return who
