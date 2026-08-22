"""Price-drop alerts over data/history.jsonl + current deals."""

import json
import time

from .deals import DATA_DIR, load_deals, load_history

ALERTS_STATE = DATA_DIR / "alerts_state.json"
DROP_MIN_USD = 1.50
DROP_MIN_PCT = 0.10
SCREAM_PRICE_USD = 10.00


def _load_state():
    if not ALERTS_STATE.exists():
        return {}
    try:
        return json.loads(ALERTS_STATE.read_text())
    except json.JSONDecodeError:
        return {}


def _save_state(state):
    ALERTS_STATE.parent.mkdir(parents=True, exist_ok=True)
    ALERTS_STATE.write_text(json.dumps(state))


def check():
    """Return list of alert dicts (kind, title, price, prev, site, url)."""
    out = []
    history = load_history()
    for ident, snaps in history.items():
        if len(snaps) < 2:
            continue
        a, b = snaps[-2], snaps[-1]
        if a["used_price"] is None or b["used_price"] is None:
            continue
        prev, cur = a["used_price"], b["used_price"]
        drop = prev - cur
        if drop >= DROP_MIN_USD or (prev > 0 and drop / prev >= DROP_MIN_PCT):
            out.append({
                "kind": "drop",
                "title": ident[:60],
                "price": cur,
                "prev": prev,
                "pct_off": b.get("pct_off"),
                "site": b.get("site", ""),
            })

    for r in load_deals():
        if r.get("quality") and r["used_price"] <= SCREAM_PRICE_USD:
            out.append({
                "kind": "scream",
                "title": r["title"][:60],
                "price": r["used_price"],
                "prev": None,
                "pct_off": r.get("pct_off"),
                "site": r.get("site", "wob"),
                "url": r.get("url", ""),
            })
    # newest first, drops before screams
    out.sort(key=lambda a: (a["kind"] != "drop", a["price"]))
    return out


def new_since_last(alerts):
    state = _load_state()
    seen = set(state.get("alerted", []))
    fresh = [a for a in alerts if f"{a['kind']}|{a['title']}|{a['price']}" not in seen]
    if fresh:
        state["alerted"] = list(seen | {
            f"{a['kind']}|{a['title']}|{a['price']}" for a in fresh
        })
        state["last_run"] = time.time()
        _save_state(state)
    return fresh


def notify(alerts):
    import subprocess
    if not alerts:
        return
    drops = [a for a in alerts if a["kind"] == "drop"]
    screams = [a for a in alerts if a["kind"] == "scream"]
    msg = []
    if drops:
        msg.append(f"{len(drops)} price drop(s)")
    if screams:
        msg.append(f"{len(screams)} Q-tier book(s) under ${SCREAM_PRICE_USD:.0f}")
    title = "wob alerts: " + ", ".join(msg)
    body = "; ".join(f"{a['title'][:40]} ${a['price']:.2f}" for a in alerts[:3])
    subprocess.run([
        "osascript", "-e",
        f'display notification "{body}" with title "wob" sound name "Glass"',
    ], capture_output=True)
    subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], capture_output=True)
    print(title + " — " + body)