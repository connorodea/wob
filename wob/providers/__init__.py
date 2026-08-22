"""Provider registry: named price/metadata sources for the cross-web search.

A provider module must expose:
    NAME: str            - short id (used in --sites)
    ENABLED: bool        - False when keys/env are missing
    lookup(isbn13) -> dict or None
        dict keys: site, title, condition, price (float or None), currency,
        url, source ("retail"|"marketplace"|"metadata"), meta (dict)
    search(term, limit=5) -> list[dict]   (optional; metadata-style hits)
"""

import importlib

_MODULES = ("openlibrary", "googlebooks", "googleshopping", "amazon", "ebay")
_CACHE = {}


def load(name):
    if name in _CACHE:
        return _CACHE[name]
    mod = importlib.import_module(f".{name}", __package__)
    _CACHE[name] = mod
    return mod


def available():
    """Return {name: module} for providers that can run (ENABLED)."""
    out = {}
    for name in _MODULES:
        try:
            mod = load(name)
        except Exception:
            continue
        if getattr(mod, "ENABLED", False):
            out[name] = mod
    return out


def names():
    return list(_MODULES)


def health():
    """Deterministic connector health: enabled flag + missing keys.

    No network. Each module reports ENABLED and, when disabled, which
    credential pairs are missing. Consumers can gate paid lookups on this.
    """
    from ..config import load_config

    cfg = load_config()
    need = {
        "ebay": ("ebay_app_id+ebay_access_token", cfg.has_ebay_creds),
        "googleshopping": ("dataforseo_login+dataforseo_password", cfg.has_dataforseo_creds),
        "amazon": ("dataforseo_login+dataforseo_password", cfg.has_dataforseo_creds),
    }
    out = []
    for name in _MODULES:
        try:
            mod = load(name)
            enabled = bool(getattr(mod, "ENABLED", False))
        except Exception:
            enabled = False
        entry = {"name": name, "enabled": enabled, "missing": None}
        if name in need:
            what, ok = need[name]
            entry["enabled"] = enabled and ok
            if not ok:
                entry["missing"] = what
        out.append(entry)
    return out
