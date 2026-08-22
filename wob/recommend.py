"""Recommendation engine: books adjacent to what you like, ranked by
relevance and current discount.

Adjacency comes from data we already own:
  - title-token Jaccard similarity (curated token lists, author stripped)
  - co-membership in course packs (editions/topics cluster naturally)
  - current deal discount as a boost (recommendations you can buy NOW)
No model, no API — deterministic and inspectable.
"""

from difflib import SequenceMatcher

from .coursepacks import COURSEPACKS
from .curated import _norm_multi
from .deals import load_deals

_STOP = {"the", "a", "an", "and", "for", "with", "of", "to", "learning"}


def _phrase(tokens):
    if not tokens:
        return ""
    body = tokens[1:] if len(tokens) > 1 else tokens
    return " ".join(t for t in body if t not in _STOP and len(t) >= 3)


def _title_tokens(tokens):
    if not tokens:
        return frozenset()
    body = tokens[1:] if len(tokens) > 1 else tokens
    return frozenset(t for t in body if t not in _STOP and len(t) >= 3)


_INDEX = None


def _index():
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    from .curated import CURATED

    _INDEX = {
        label: {
            "label": label,
            "tokens": tuple(tokens),
            "title_tokens": _title_tokens(tuple(tokens)),
            "phrase": _phrase(tuple(tokens)),
            "norm": _norm_multi(label),
        }
        for label, tokens in CURATED
    }
    return _INDEX


def resolve_seed(text):
    """Free-text phrase -> best curated entry label, or a token fallback."""
    q = _norm_multi(text)
    best_label, best_score = None, 0.0
    for label, e in _index().items():
        s = SequenceMatcher(None, q, e["norm"]).ratio()
        if s > best_score:
            best_label, best_score = label, s
    if best_label and best_score > 0.45:
        return best_label
    return None


def recommend(texts, top=5):
    idx = _index()
    seeds = [idx[t] for t in (resolve_seed(t) for t in texts) if t]
    if not seeds:
        return []
    seed_labels = {s["label"] for s in seeds}

    scores = {}
    for e in idx.values():
        if e["label"] in seed_labels:
            continue
        best_sim, co_pack = 0.0, 0
        for s in seeds:
            if s["phrase"] and e["phrase"]:
                best_sim = max(best_sim, SequenceMatcher(None, s["phrase"], e["phrase"]).ratio())
        for _n, books in COURSEPACKS.values():
            labels = {b[0] for b in books}
            if seed_labels & labels and e["label"] in labels:
                co_pack += 0.5
                break
        if best_sim < 0.25 and not co_pack:
            continue
        scores[e["label"]] = {"label": e["label"], "sim": round(best_sim + co_pack, 3),
                              "price": None, "pct_off": None, "site": "", "url": "",
                              "cond": "", "title": ""}

    for r in load_deals():
        hay = _norm_multi(r.get("title", ""), r.get("handle", "") + " " + r.get("author", ""))
        for label, row in scores.items():
            e = idx[label]
            if all(_norm_multi(t) in hay for t in e["tokens"]):
                if row["price"] is None or r["used_price"] < row["price"]:
                    row.update(price=r["used_price"], pct_off=r["pct_off"],
                               site=r.get("site", "wob"), url=r.get("url", ""),
                               cond=r.get("condition", ""), title=r.get("title", ""))

    ranked = sorted(
        scores.values(),
        key=lambda r: -(r["sim"] + (r["pct_off"] or 0) * 0.25),
    )
    return ranked[:top]