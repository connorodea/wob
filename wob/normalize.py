"""Deterministic normalization for book metadata (Milestone 1, opener).

Every function is pure: same input -> same output, no network, no model.
Nothing here is ML; these are the canonical forms every later layer
(matching, dedupe, fair value) reads.

Currency conversions only happen with an explicit rate hint; without one
the function returns None (never a made-up number).
"""

from __future__ import annotations

import re
import unicodedata

FORMATS = {
    "hardcover",
    "paperback",
    "mass_market_paperback",
    "ebook",
    "audiobook",
    "unknown",
}

LANG_MAP = {
    "english": "en",
    "german": "de",
    "deutsch": "de",
    "french": "fr",
    "francais": "fr",
    "français": "fr",
    "spanish": "es",
    "espanol": "es",
    "español": "es",
    "italian": "it",
    "italiano": "it",
    "chinese": "zh",
    "japanese": "ja",
    "russian": "ru",
    "portuguese": "pt",
    "dutch": "nl",
    "polish": "pl",
    "arabic": "ar",
    "korean": "ko",
    "turkish": "tr",
}

CURRENCIES = {
    "USD": "USD",
    "$": "USD",
    "US$": "USD",
    "DOLLARS": "USD",
    "DOLLAR": "USD",
    "GBP": "GBP",
    "£": "GBP",
    "POUNDS": "GBP",
    "POUND": "GBP",
    "STERLING": "GBP",
    "EUR": "EUR",
    "€": "EUR",
    "EUROS": "EUR",
    "EURO": "EUR",
    "CAD": "CAD",
    "AUD": "AUD",
    "INR": "INR",
}

_WS = re.compile(r"\s+")
_PUNCT_EDGE = re.compile(r"^[\s.,;:()\[\]\"'!?-]+|[\s.,;:()\[\]\"'!?-]+$")
_YEAR = re.compile(r"(?<!\d)(1[4-9]\d{2}|20\d{2}|2100)(?!\d)")
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _fold(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = text.encode("ascii", "ignore").decode()
    return _WS.sub(" ", text).strip()


def normalize_title(raw: str) -> str:
    """Fold accents + case, collapse spaces. Subtitles are KEPT — they
    carry identifying words; callers decide how to use them."""
    text = _fold(raw)
    return text.lower()


def normalize_author(raw: str) -> str:
    """'Last, First' -> 'First Last'; otherwise as-is, folded + lowercased."""
    text = _fold(raw)
    if not text:
        return ""
    if "," in text:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        text = " ".join(reversed(parts))
    return text.lower()


_LEGAL_FORM = re.compile(
    r"(?i)\b(incorporated|inc|corp|corporation|ltd|llc|limited|plc|co|company|"
    r"& co|publishing group|publisher|press usa|usa)\b\.?",
)


def normalize_publisher(raw: str) -> str:
    """Fold accents/case; strip legal-form suffixes (Inc, Ltd, LLC...)."""
    text = _fold(raw)
    if not text:
        return ""
    text = _LEGAL_FORM.sub(" ", text)
    text = _WS.sub(" ", text).strip(" ,&.-")
    return text.lower()


def normalize_format(raw: str) -> str:
    """Map common strings to the canonical format set."""
    text = _fold(raw).lower()
    if not text:
        return "unknown"
    if "mass market" in text or "pocket" in text or "mass-market" in text:
        return "mass_market_paperback"
    if "paperback" in text or "paper back" in text or "softcover" in text:
        return "paperback"
    if "hardcover" in text or "hardback" in text or "hard cover" in text:
        return "hardcover"
    if "kindle" in text or "ebook" in text or "e-book" in text or "digital" in text:
        return "ebook"
    if "audio" in text or "cd" in text and "audio" in text or "mp3" in text:
        return "audiobook"
    return "unknown"


def normalize_language(raw: str) -> str:
    """Common language names -> ISO 639-1; unknown input passes through folded."""
    text = _fold(raw).lower()
    if not text:
        return ""
    return LANG_MAP.get(text, text)


def normalize_publication_date(raw: str) -> tuple[int | None, int | None, int | None]:
    """Parse lenient date strings -> (year, month, day); unknown parts are None.

    Handles: '2022', 'May 2020', '2020-05-14', '05/14/2020', '14 May 2020'.
    """
    text = _fold(raw)
    if not text:
        return (None, None, None)

    # ISO / slash forms first
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        return (y, mo, d) if 1 <= mo <= 12 and 1 <= d <= 31 else (y, mo, None)
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        mo, d, y = (int(x) for x in m.groups())
        return (y, mo, d) if 1 <= mo <= 12 and 1 <= d <= 31 else (y, mo, None)

    ym = re.fullmatch(r"(\d{4})[-/.](\d{1,2})", text)
    if ym:
        return (int(ym.group(1)), int(ym.group(2)), None)

    # year only
    y = _YEAR.search(text)
    if y and re.fullmatch(r"\d{4}", text):
        return (int(y.group(1)), None, None)

    # month-name forms
    for name, num in _MONTHS.items():
        if text.lower().startswith(name):
            m = re.fullmatch(rf"{name}\.?[,\s]+(\d{{4}})", text, re.I)
            if m:
                return (int(m.group(1)), num, None)
            m2 = re.fullmatch(rf"{name}\.?[,\s]+(\d{{1,2}})[,\s]+(\d{{4}})", text, re.I)
            if m2:
                return (int(m2.group(2)), num, int(m2.group(1)))
            return (None, num, None)
        m3 = re.fullmatch(rf"(\d{{1,2}})[,\s]+{name}\.?[,\s]+(\d{{4}})", text, re.I)
        if m3:
            return (int(m3.group(2)), num, int(m3.group(1)))

    y = _YEAR.search(text)
    return (int(y.group(1)), None, None) if y else (None, None, None)


def normalize_currency(raw: str) -> str:
    """Currency aliases -> ISO code; unknown input uppercased as-is."""
    text = _fold(raw).upper()
    if not text:
        return ""
    return CURRENCIES.get(text, text)


def to_usd_cents(amount: float, currency: str, rate_hint: dict | None) -> int | None:
    """Convert an amount in `currency` to USD cents.

    Requires an explicit rate_hint {code: usd_per_unit}; returns None when
    the rate is unknown — never fabricates a conversion.
    """
    code = normalize_currency(currency)
    if not code or amount is None:
        return None
    if code == "USD":
        return int(round(amount * 100))
    rate = (rate_hint or {}).get(code)
    if rate is None or rate <= 0:
        return None
    return int(round(amount * rate * 100))
