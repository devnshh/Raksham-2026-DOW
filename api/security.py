"""
Shared secrets and API-key checks for SATARK.

Keys come from environment variables. Nothing is hard-coded: if a key is not set,
a random one is generated for this process and logged once, so a fresh checkout is
never protected by a well-known default.
"""

import logging
import os
import secrets
from typing import Optional

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


def require_analyst_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> bool:
    """FastAPI dependency: accepts `X-API-Key: <key>` or `Authorization: Bearer <key>`."""
    provided = x_api_key
    if not provided and authorization:
        provided = authorization[7:].strip() if authorization.lower().startswith("bearer ") else authorization.strip()
    if not provided or not secrets.compare_digest(provided, analyst_key()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: invalid or missing analyst API key",
        )
    return True
