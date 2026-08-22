"""ISBN/barcode normalization. Wraps isbnlib with a stdlib fallback."""

import re

try:
    import isbnlib
except ImportError:  # pragma: no cover
    isbnlib = None

_RE_NONISBN = re.compile(r"[^0-9xX]")


def clean(value):
    """Strip an ISBN-like string down to digits and X only, else None."""
    if value is None:
        return None
    s = _RE_NONISBN.sub("", str(value)).upper()
    return s or None


def canonical(value):
    """Return a clean ISBN (digits+X, X upper) or None if nothing ISBN-like."""
    return clean(value)


def is_valid13(value):
    s = clean(value)
    if not s or len(s) != 13 or not s.isdigit():
        return False
    total = sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(s))
    return total % 10 == 0


def to13(value):
    """Normalize to ISBN-13 string, or None. Handles ISBN-10 and EAN-13 input."""
    s = clean(value)
    if not s:
        return None
    if len(s) == 13 and s.isdigit() and is_valid13(s):
        return s
    if len(s) == 13 and s.isdigit():
        return s  # malformed checksum: still the best GTIN we have
    if len(s) == 10:
        if isbnlib is not None:
            try:
                out = isbnlib.to_isbn13(s)
                if out:
                    return out
            except Exception:
                pass
        return _to13_stdlib(s)
    return None


def _to13_stdlib(isbn10):
    body = "978" + isbn10[:9]
    total = sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(body))
    return body + str((10 - total % 10) % 10)


def ean13(value):
    """Return the 13-digit GTIN (ISBN-13) for barcode use, or None."""
    return to13(value)


def mask(value):
    """Hyphenated display form via isbnlib, else the clean digits."""
    s = clean(value)
    if not s:
        return ""
    if isbnlib is not None and len(s) in (10, 13):
        try:
            return isbnlib.mask(s)
        except Exception:
            pass
    return s