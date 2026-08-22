"""wob domain entities — the typed core every model reads and writes.

Versioned dataclasses with `validate()` (raises ValueError), `to_dict()`,
and `from_dict()`. Single source of truth for normalization vocabulary:
conditions, purchase modes, currency. schema_version records the shape so
stored JSONL can migrate explicitly.

No ML here — pure representation contracts (Milestone 0).
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

SCHEMA_VERSION = "entities/1.0"

CANONICAL_CONDITIONS = {
    "NEW",
    "LIKE_NEW",
    "VERY_GOOD",
    "GOOD",
    "WELL_READ",
    "ACCEPTABLE",
    "UNKNOWN",
}
PURCHASE_MODES = {
    "observe_only",
    "recommend_only",
    "confirmation_required",
    "autonomous_within_policy",
}
REQUIREMENT_LEVELS = {"required", "recommended", "optional", "supplementary"}
CURRENCIES = {"USD", "GBP", "EUR"}


def _err(name, why):
    return ValueError(f"{name}: {why}")


@dataclasses.dataclass
class Entity:
    VERSION: ClassVar[str] = "1.0"  # class attribute, not an init field

    def validate(self):
        raise NotImplementedError

    def to_dict(self):
        return {"_type": type(self).__name__, "_version": "1.0", **dataclasses.asdict(self)}

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if k not in ("_version", "_type")})


@dataclasses.dataclass
class BookWork(Entity):
    work_id: str
    title: str
    author_names: list[str]
    editionless_key: str

    def validate(self):
        if not self.work_id or not isinstance(self.work_id, str):
            raise _err("work_id", "required string")
        if not isinstance(self.title, str) or not self.title.strip():
            raise _err("title", "required non-empty string")
        if not isinstance(self.author_names, list) or not all(
            isinstance(a, str) for a in self.author_names
        ):
            raise _err("author_names", "list[str]")
        if not isinstance(self.editionless_key, str) or not self.editionless_key:
            raise _err("editionless_key", "required string")


@dataclasses.dataclass
class BookEdition(Entity):
    edition_id: str
    work_id: str
    title: str
    authors: list[str]
    publisher: str
    format: str
    language: str
    published_year: int | None

    def validate(self):
        if not self.edition_id:
            raise _err("edition_id", "required string")
        if not self.title.strip():
            raise _err("title", "required")
        if not isinstance(self.authors, list):
            raise _err("authors", "list[str]")
        if self.published_year is not None and not (
            isinstance(self.published_year, int) and 1400 <= self.published_year <= 2100
        ):
            raise _err("published_year", "int in [1400,2100] or None")


@dataclasses.dataclass
class BookIdentifier(Entity):
    kind: str
    value: str
    primary: bool

    def validate(self):
        if self.kind not in {"isbn10", "isbn13", "asin", "ean"}:
            raise _err("kind", "one of isbn10/isbn13/asin/ean")
        if not isinstance(self.value, str) or not self.value:
            raise _err("value", "required string")
        if self.kind == "isbn13" and not (len(self.value) == 13 and self.value.isdigit()):
            raise _err("value", "isbn13 must be 13 digits")
        if self.kind == "isbn10" and not (
            len(self.value) == 10 and (self.value[:9].isdigit() and self.value[9] in "0123456789Xx")
        ):
            raise _err("value", "isbn10 must be 10 chars ending in digit/X")


@dataclasses.dataclass
class BookOffer(Entity):
    offer_id: str
    edition_id: str
    seller_id: str
    condition: str
    price_cents: int
    currency: str
    shipping_cents: int
    url: str
    source: str
    retrieved_at: str
    landed_cost_cents: int

    def validate(self):
        if not self.offer_id:
            raise _err("offer_id", "required string")
        if self.condition not in CANONICAL_CONDITIONS:
            raise _err("condition", f"unknown canonical condition {self.condition!r}")
        if self.currency not in CURRENCIES:
            raise _err("currency", f"must be one of {sorted(CURRENCIES)}")
        for f in ("price_cents", "shipping_cents", "landed_cost_cents"):
            v = getattr(self, f)
            if not isinstance(v, int) or v < 0:
                raise _err(f, "non-negative int")
        if not self.source:
            raise _err("source", "required string (connector name)")


@dataclasses.dataclass
class Seller(Entity):
    seller_id: str
    name: str
    site: str
    trust_score: float | None

    def validate(self):
        if not self.seller_id:
            raise _err("seller_id", "required string")
        if self.trust_score is not None and not (
            isinstance(self.trust_score, (int, float)) and 0.0 <= self.trust_score <= 1.0
        ):
            raise _err("trust_score", "float in [0,1] or None")


@dataclasses.dataclass
class ConditionAssessment(Entity):
    condition: str
    source_vocabulary: str | None
    confidence: float | None

    def validate(self):
        if self.condition not in CANONICAL_CONDITIONS:
            raise _err("condition", f"unknown canonical condition {self.condition!r}")
        if self.confidence is not None and not (
            isinstance(self.confidence, (int, float)) and 0.0 <= self.confidence <= 1.0
        ):
            raise _err("confidence", "float in [0,1] or None")


@dataclasses.dataclass
class UserProfile(Entity):
    user_id: str
    interests: list[str]
    favored_authors: list[str]
    min_condition: str
    budget_cents: int | None

    def validate(self):
        if not self.user_id:
            raise _err("user_id", "required string")
        if not isinstance(self.interests, list):
            raise _err("interests", "list[str]")
        if self.min_condition not in CANONICAL_CONDITIONS:
            raise _err("min_condition", f"canonical condition, got {self.min_condition!r}")
        if self.budget_cents is not None and (
            not isinstance(self.budget_cents, int) or self.budget_cents < 0
        ):
            raise _err("budget_cents", "non-negative int or None")


@dataclasses.dataclass
class ReadingList(Entity):
    list_id: str
    user_id: str
    title: str
    items: list[dict]

    def validate(self):
        if not self.list_id:
            raise _err("list_id", "required string")
        if not isinstance(self.items, list):
            raise _err("items", "list[dict]")
        for item in self.items:
            if not isinstance(item, dict) or not isinstance(item.get("book"), str):
                raise _err("items", "each item needs a 'book' string")
            if item.get("required") not in REQUIREMENT_LEVELS:
                raise _err("items", f"required must be one of {sorted(REQUIREMENT_LEVELS)}")


@dataclasses.dataclass
class Recommendation(Entity):
    rec_id: str
    user_id: str
    edition_id: str
    reasons: list[str]
    confidence: float | None
    model_id: str
    created_at: str

    def validate(self):
        if not self.rec_id:
            raise _err("rec_id", "required string")
        if not isinstance(self.reasons, list) or not self.reasons:
            raise _err("reasons", "non-empty list[str] (explanations)")
        if self.confidence is not None and not (
            isinstance(self.confidence, (int, float)) and 0.0 <= self.confidence <= 1.0
        ):
            raise _err("confidence", "float in [0,1] or None")
        if not self.model_id:
            raise _err("model_id", "required string")


@dataclasses.dataclass
class Watchlist(Entity):
    watch_id: str
    user_id: str
    edition_id: str
    target_price_cents: int | None
    min_condition: str
    active: bool

    def validate(self):
        if not self.watch_id:
            raise _err("watch_id", "required string")
        if self.target_price_cents is not None and (
            not isinstance(self.target_price_cents, int) or self.target_price_cents < 0
        ):
            raise _err("target_price_cents", "non-negative int or None")
        if self.min_condition not in CANONICAL_CONDITIONS:
            raise _err("min_condition", "canonical condition")


@dataclasses.dataclass
class PurchasePolicy(Entity):
    policy_id: str
    user_id: str
    mode: str
    budget_monthly_cents: int
    seller_allowlist: list[str]
    seller_blocklist: list[str]
    min_condition: str

    def validate(self):
        if not self.policy_id:
            raise _err("policy_id", "required string")
        if self.mode not in PURCHASE_MODES:
            raise _err("mode", f"one of {sorted(PURCHASE_MODES)}")
        if self.mode == "autonomous_within_policy" and (
            not isinstance(self.budget_monthly_cents, int) or self.budget_monthly_cents <= 0
        ):
            raise _err("budget_monthly_cents", "positive int required for autonomous mode")
        if not isinstance(self.seller_allowlist, list) or not isinstance(
            self.seller_blocklist, list
        ):
            raise _err("seller lists", "list[str]")
        if self.min_condition not in CANONICAL_CONDITIONS:
            raise _err("min_condition", "canonical condition")


@dataclasses.dataclass
class OpportunityScore(Entity):
    score: float
    version: str
    inputs: dict
    explanation: str
    computed_at: str

    def validate(self):
        if not (isinstance(self.score, (int, float)) and 0.0 <= self.score <= 1.0):
            raise _err("score", "float in [0,1]")
        if not isinstance(self.version, str) or not self.version:
            raise _err("version", "non-empty version string (e.g. wos/1.0)")
        if not isinstance(self.inputs, dict):
            raise _err("inputs", "dict")
        if not self.explanation.strip():
            raise _err("explanation", "non-empty explanation string")


@dataclasses.dataclass
class PredictionProvenance(Entity):
    pred_id: str
    model_id: str
    model_version: str
    inputs_hash: str
    dataset_ref: str | None
    run_id: str | None

    def validate(self):
        if not self.pred_id:
            raise _err("pred_id", "required string")
        if not self.model_id or not self.model_version:
            raise _err("model", "model_id + model_version required")
        if not isinstance(self.inputs_hash, str) or len(self.inputs_hash) < 8:
            raise _err("inputs_hash", "hash string")


ALL_ENTITIES = [
    BookWork,
    BookEdition,
    BookIdentifier,
    BookOffer,
    Seller,
    ConditionAssessment,
    UserProfile,
    ReadingList,
    Recommendation,
    Watchlist,
    PurchasePolicy,
    OpportunityScore,
    PredictionProvenance,
]
