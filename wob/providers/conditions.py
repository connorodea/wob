"""Condition vocabularies per marketplace, mapped to the canonical set.

Canonical: NEW, LIKE_NEW, VERY_GOOD, GOOD, ACCEPTABLE, UNKNOWN.
(WELL_READ is WoB-specific and mapped from its own pipeline, not here.)
"""


def ebay_condition_map():
    table = {
        "Brand New": "NEW",
        "Like New": "LIKE_NEW",
        "Very Good": "VERY_GOOD",
        "Good": "GOOD",
        "Acceptable": "ACCEPTABLE",
    }

    def _map(s):
        if not s:
            return "UNKNOWN"
        if s in table:
            return table[s]
        key = "".join(ch for ch in s.lower() if ch.isalnum())
        return {
            "brandnew": "NEW",
            "likenew": "LIKE_NEW",
            "verygood": "VERY_GOOD",
            "good": "GOOD",
            "acceptable": "ACCEPTABLE",
        }.get(key, "UNKNOWN")

    return _map


ABEBOOKS_CONDITIONS = {
    "Brand New": "NEW",
    "New": "NEW",
    "Used - Like New": "LIKE_NEW",
    "As New": "LIKE_NEW",
    "Fine": "LIKE_NEW",
    "Near Fine": "LIKE_NEW",
    "Very Good": "VERY_GOOD",
    "Very Good Minus": "VERY_GOOD",
    "Good": "GOOD",
    "Good Minus": "GOOD",
    "Fair": "ACCEPTABLE",
    "Poor": "ACCEPTABLE",
    "Unacceptable": "UNKNOWN",
}

ALIBRIS_CONDITIONS = {
    "New": "NEW",
    "Used - Like New": "LIKE_NEW",
    "Used - Very Good": "VERY_GOOD",
    "Used - Good": "GOOD",
    "Used - Acceptable": "ACCEPTABLE",
    "Collectible": "UNKNOWN",
}

BIBLIO_CONDITIONS = {
    "New": "NEW",
    "As New": "LIKE_NEW",
    "Fine": "LIKE_NEW",
    "Near Fine": "LIKE_NEW",
    "Very Good": "VERY_GOOD",
    "Good": "GOOD",
    "Fair": "ACCEPTABLE",
    "Poor": "ACCEPTABLE",
    "Reading Copy": "ACCEPTABLE",
}

THRIFTBOOKS_CONDITIONS = {
    "New": "NEW",
    "Like New": "LIKE_NEW",
    "Very Good": "VERY_GOOD",
    "Good": "GOOD",
    "Acceptable": "ACCEPTABLE",
}


def abebooks_condition_map():
    return ABEBOOKS_CONDITIONS.get


def alibris_condition_map():
    return ALIBRIS_CONDITIONS.get


def biblio_condition_map():
    return BIBLIO_CONDITIONS.get


def thriftbooks_condition_map():
    return THRIFTBOOKS_CONDITIONS.get


def map_condition(provider, value):
    fn = {
        "ebay": ebay_condition_map(),
        "abebooks": abebooks_condition_map(),
        "alibris": alibris_condition_map(),
        "biblio": biblio_condition_map(),
        "thriftbooks": thriftbooks_condition_map(),
    }.get(provider)
    return fn(value) if fn else "UNKNOWN"