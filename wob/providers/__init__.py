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