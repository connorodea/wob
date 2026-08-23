"""M4 opener: deterministic user-interest profiles + cold-start affinity.

No ML: profiles are explicit (interests, favored authors, budget,
minimum condition) and affinity is token overlap with explanations.
Every recommendation reason is a readable string.
"""

from __future__ import annotations

from .entities import UserProfile
from .normalize import normalize_author, normalize_title


def build_profile(
    user_id: str,
    interests: list[str],
    favored_authors: list[str] | None = None,
    min_condition: str = "GOOD",
    budget_cents: int | None = None,
) -> UserProfile:
    p = UserProfile(
        user_id=user_id,
        interests=[i.strip().lower() for i in interests if i and i.strip()],
        favored_authors=[normalize_author(a) for a in (favored_authors or []) if a and a.strip()],
        min_condition=min_condition,
        budget_cents=budget_cents,
    )
    p.validate()
    return p


def _tokens(text):
    return {w for w in normalize_title(text).split() if len(w) >= 3}


def affinity(profile: UserProfile, title: str, author: str) -> tuple[float, list[str]]:
    """Interest affinity in [0,1] + the reasons that produced it."""
    t = _tokens(title)
    a = normalize_author(author)
    reasons: list[str] = []

    hits = 0
    for interest in profile.interests:
        it = _tokens(interest)
        if it & t:
            hits += 1
            reasons.append(f"matches your interest in '{interest}'")
    for fav in profile.favored_authors:
        if fav and fav in a:
            hits += 1
            reasons.append(f"by an author you favor ({author.strip()})")

    base = min(hits / max(len(profile.interests), 1), 1.0)
    score = min(0.4 + 0.6 * base, 1.0) if hits else 0.2
    return round(score, 4), reasons[:4]
