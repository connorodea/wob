CONDITION_PRIORITY = {
    "NEW": 6,
    "LIKE_NEW": 5,
    "VERY_GOOD": 4,
    "GOOD": 3,
    "WELL_READ": 2,
    "ACCEPTABLE": 1,
}

TIE_FRACTION = 0.15
TIE_ABSOLUTE = 1.50


def pick_best(candidates):
    if not candidates:
        return None
    best_price = min(c["used_price"] for c in candidates)
    near = [
        c
        for c in candidates
        if c["used_price"] <= best_price + TIE_ABSOLUTE
        or c["used_price"] <= best_price * (1 + TIE_FRACTION)
    ]
    return max(
        near,
        key=lambda c: (
            CONDITION_PRIORITY.get(c["condition"], 0),
            -c["used_price"],
            c["pct_off"],
        ),
    )