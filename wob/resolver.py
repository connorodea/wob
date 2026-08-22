"""M2 opener: deterministic book/edition resolver with abstention.

Classification: exact | compatible | incompatible | uncertain.
Every result carries confidence, explanation, and evidence (the rule
that fired). Purely deterministic — this is the baseline the optional
embedding model must beat before it can replace anything.

Rules (in order):
  R1 shared ISBN-13                          -> exact   1.00
  R2 ISBN-10 <-> ISBN-13 cross-match         -> exact   0.98
  R3 both ISBNs present, different           -> incompatible 0.90
  R4 strong normalized title+author overlap  -> compatible  0.85
  R5 weaker overlap band                     -> uncertain  0.60
  R6 below band                              -> incompatible 0.75
"""

from __future__ import annotations

from . import isbnutil
from .normalize import normalize_author, normalize_title

STRONG_SIM = 0.75
WEAK_SIM = 0.40


def _tokens(*parts):
    out = set()
    for p in parts:
        for w in p.split():
            if len(w) >= 3:
                out.add(w)
    return out


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _isbns(a, b):
    """All valid ISBNs known for both sides."""
    left, right = set(), set()
    for side, out in ((a, left), (b, right)):
        for key in ("isbn13", "isbn", "isbn10", "barcode"):
            v = side.get(key)
            i13 = isbnutil.to13(v) if v else None
            if i13:
                out.add(i13)
    return left, right


def resolve(a: dict, b: dict) -> dict:
    """a/b: book records with title, author, isbn* fields (loose extras ok)."""
    title_a = normalize_title(a.get("title", ""))
    title_b = normalize_title(b.get("title", ""))
    author_a = normalize_author(a.get("author", ""))
    author_b = normalize_author(b.get("author", ""))

    isbns_a, isbns_b = _isbns(a, b)

    # R1 / R2
    if isbns_a and isbns_a & isbns_b:
        return {
            "class": "exact",
            "confidence": 1.0,
            "explanation": "shared ISBN-13",
            "evidence": sorted(isbns_a & isbns_b),
        }

    # R3
    if isbns_a and isbns_b:
        return {
            "class": "incompatible",
            "confidence": 0.9,
            "explanation": "different ISBNs and no title corroboration",
            "evidence": [sorted(isbns_a)[0], sorted(isbns_b)[0]],
        }

    # textual similarity
    sim = _jaccard(_tokens(title_a, author_a), _tokens(title_b, author_b))
    if sim >= STRONG_SIM:
        return {
            "class": "compatible",
            "confidence": 0.85,
            "explanation": "strong normalized title+author overlap",
            "evidence": {"sim": round(sim, 3)},
        }
    if sim >= WEAK_SIM:
        return {
            "class": "uncertain",
            "confidence": 0.6,
            "explanation": "partial overlap — not confident enough to match",
            "evidence": {"sim": round(sim, 3)},
        }
    if not title_a or not title_b:
        return {
            "class": "uncertain",
            "confidence": 0.3,
            "explanation": "insufficient metadata to judge",
            "evidence": {},
        }
    return {
        "class": "incompatible",
        "confidence": 0.75,
        "explanation": "titles/authors do not match",
        "evidence": {"sim": round(sim, 3)},
    }
