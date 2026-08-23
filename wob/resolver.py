"""M2 opener: deterministic book/edition resolver with abstention.

Classification: exact | compatible | incompatible | uncertain.
Every result carries confidence, explanation, and evidence (the rule
that fired). Purely deterministic — this is the baseline the optional
embedding model must beat before it can replace anything.

Rules:
  R1 shared ISBN-13                       -> exact   1.00
  R2 ISBN-10 <-> ISBN-13 cross-match      -> exact   0.98
  R3 differing ISBNs -> work-identity check (coverage + author gate)
  R4 strong normalized title coverage     -> compatible
  R5 partial overlap / unconfirmed author -> uncertain
  R6 below threshold                      -> incompatible
"""

from __future__ import annotations

from . import isbnutil
from .normalize import normalize_author, normalize_title


def _tokens(*parts):
    out = set()
    for p in parts:
        for w in p.split():
            w = w.strip(".,;:()[]!?-")
            if len(w) >= 3:
                out.add(w)
    return out


GENERIC = {
    "machine",
    "learning",
    "deep",
    "python",
    "data",
    "science",
    "introduction",
    "hands-on",
    "algorithms",
    "artificial",
    "intelligence",
    "modern",
    "approach",
    "with",
    "for",
    "and",
    "analysis",
    "system",
    "systems",
    "design",
    "clean",
    "computer",
    "networking",
    "network",
    "programming",
    "the",
    "you",
    "your",
    "practical",
    "linear",
    "algebra",
    "calculus",
    "statistics",
    "probability",
    "mathematics",
    "math",
    "theory",
    "fundamentals",
    "applications",
    "applied",
    "advanced",
    "series",
    "books",
    "guide",
    "its",
}
EDITION_MARKERS = {
    "2nd",
    "3rd",
    "4th",
    "5th",
    "6th",
    "7th",
    "8th",
    "9th",
    "10th",
    "edition",
    "ed",
    "vol",
    "volume",
    "second",
    "third",
    "fourth",
    "global",
}


def _distinctive(tokens):
    return tokens - GENERIC - EDITION_MARKERS


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


def _text_verdict(title_a, author_a, title_b, author_b):
    """Coverage-based work-identity verdict for two non-ISBN-matching sides."""
    ta = _tokens(title_a)
    tb = _tokens(title_b)
    au = _tokens(author_a)
    ab = _tokens(author_b)
    shared = ta & tb
    cov = len(shared) / min(len(ta), len(tb)) if ta and tb else 0.0
    author_match = bool(au & ab)
    distinctive = _distinctive(shared)
    extra = (ta | tb) - shared - EDITION_MARKERS

    if not title_a or not title_b or not author_a or not author_b:
        return {
            "class": "uncertain",
            "confidence": 0.3,
            "explanation": "insufficient metadata to judge",
            "evidence": {"cov": round(cov, 3)},
        }

    # strong identity: real identifying title words, or (near-)identical
    # titles from the same author (new edition / subtitle changes)
    if len(distinctive) >= 2 or (cov >= 0.6 and distinctive and author_match and not extra):
        return {
            "class": "compatible",
            "confidence": 0.85 if author_match else 0.7,
            "explanation": "strong normalized title overlap"
            + (" + matching author" if author_match else " (author unconfirmed)"),
            "evidence": {"cov": round(cov, 3), "distinctive": sorted(distinctive)[:5]},
        }
    if cov >= 0.75 and author_match:
        return {
            "class": "compatible",
            "confidence": 0.8,
            "explanation": "identical/near-identical title + matching author",
            "evidence": {"cov": round(cov, 3)},
        }

    # ambiguous middle
    if cov >= 0.4 and author_match:
        return {
            "class": "uncertain",
            "confidence": 0.55,
            "explanation": "partial title overlap with matching author",
            "evidence": {"cov": round(cov, 3)},
        }
    if cov >= 0.4 and distinctive:
        return {
            "class": "uncertain",
            "confidence": 0.5,
            "explanation": "some identifying words overlap, authors differ",
            "evidence": {"cov": round(cov, 3), "distinctive": sorted(distinctive)[:5]},
        }

    return {
        "class": "incompatible",
        "confidence": 0.75,
        "explanation": "titles/authors do not match",
        "evidence": {"cov": round(cov, 3), "shared": sorted(shared)[:5]},
    }


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

    # R3: differing ISBNs are NOT enough to call books different — different
    # editions of the same work share no ISBN. Fall back to work identity.
    if isbns_a and isbns_b:
        verdict = _text_verdict(title_a, author_a, title_b, author_b)
        if verdict["class"] == "incompatible":
            return {
                "class": "incompatible",
                "confidence": 0.9,
                "explanation": "different ISBNs and no title corroboration",
                "evidence": [sorted(isbns_a)[0], sorted(isbns_b)[0]],
            }
        verdict["confidence"] = min(verdict["confidence"], 0.9)
        verdict["explanation"] = "different ISBNs: " + verdict["explanation"]
        return verdict

    return _text_verdict(title_a, author_a, title_b, author_b)
