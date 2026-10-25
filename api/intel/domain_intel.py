"""
SATARK Domain Intelligence Module.
Provides reputation scoring and domain age resolution for payment link entry channels.
Enforces 300ms SLA timeout, caching, and fail-unknown semantics (NEVER safe defaults).
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("satark.intel.domain")

_DOMAINS_FILE = Path(__file__).resolve().parent / "domains.json"
_DOMAIN_CACHE: Dict[str, Dict[str, Any]] = {}
_DATABASE_LOADED = False


def _load_domain_db() -> Dict[str, Dict[str, Any]]:
    """Loads domain reputation database from JSON backing store."""
    global _DATABASE_LOADED
    if not _DOMAINS_FILE.exists():
        logger.warning(f"Domains JSON file missing at {_DOMAINS_FILE}")
        return {}
    try:
        data = json.loads(_DOMAINS_FILE.read_text(encoding="utf-8"))
        _DATABASE_LOADED = True
        return data
    except Exception as exc:
        logger.error(f"Failed to parse domains database: {exc}")
        return {}


def lookup_domain(domain: Optional[str], timeout_ms: float = 300.0) -> Dict[str, Optional[Any]]:
    """
    Looks up domain reputation and domain registration age.
    Contract:
        lookup_domain(domain) -> {"bad": 0/1/None, "age_days": int/None}

    TODO: Production Threat Intelligence Integrations:
    1. Google Safe Browsing v4 / Web Risk API (real-time malware/phishing lookup)
    2. URLhaus API (Abuse.ch malicious URL & malware payload database)
    3. OpenPhish Community / Premium Feed (zero-day phishing URL detection)
    4. RDAP / WHOIS REST protocol (canonical domain creation date for true domain age)

    Rules:
    - 300 ms timeout enforced.
    - Results cached in-memory.
    - If lookup fails, domain is missing, or timed out: returns {"bad": None, "age_days": None}.
      NEVER returns a safe default (e.g. bad=0 or age=365) on failure!
    """
    if not domain or not isinstance(domain, str) or not domain.strip():
        return {"bad": None, "age_days": None}

    clean_domain = domain.strip().lower()
    # Strip protocols and paths if present (e.g. https://domain.com/path -> domain.com)
    if "://" in clean_domain:
        clean_domain = clean_domain.split("://", 1)[1]
    clean_domain = clean_domain.split("/", 1)[0].split(":", 1)[0].rstrip(".")

    # Check in-memory cache
    if clean_domain in _DOMAIN_CACHE:
        return _DOMAIN_CACHE[clean_domain]

    start_time = time.perf_counter()

    try:
        db = _load_domain_db()
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        if elapsed_ms > timeout_ms:
            logger.warning(f"Domain lookup for {clean_domain} timed out ({elapsed_ms:.1f}ms > {timeout_ms}ms)")
            return {"bad": None, "age_days": None}

        # A subdomain of a known-bad domain is bad too (www.x, pay.x): the owner of x controls them.
        parents = [".".join(clean_domain.split(".")[i:]) for i in range(1, clean_domain.count("."))]
        bad_parent = next((d for d in parents if d in db and db[d].get("bad") == 1), None)
        if clean_domain not in db and bad_parent:
            known_entry = db[bad_parent]
        else:
            known_entry = db.get(clean_domain)
        if known_entry is not None:
            entry = known_entry
            bad_val = int(entry.get("bad", 0)) if entry.get("bad") is not None else None
            age_val = int(entry.get("age_days", 0)) if entry.get("age_days") is not None else None
            result = {"bad": bad_val, "age_days": age_val}
        else:
            # Domain not in known database: return None (unknown), NEVER a safe value
            result = {"bad": None, "age_days": None}

        # Cache valid lookup
        _DOMAIN_CACHE[clean_domain] = result
        return result

    except Exception as exc:
        logger.error(f"Domain lookup failure for '{clean_domain}': {exc}")
        # On error: return unknown, NEVER safe
        return {"bad": None, "age_days": None}


def clear_cache():
    """Clears in-memory domain cache (for test isolation)."""
    _DOMAIN_CACHE.clear()
