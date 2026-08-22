import json
import time

from .session import BASE, fetch, get_session, save_cookies


def cart_contents():
    r = fetch(f"{BASE}/cart.js")
    return json.loads(r.text)


def cart_cookie():
    s = get_session()
    for c in s.cookies:
        if c.name == "cart" and "worldofbooks" in (c.domain or ""):
            return c.value
    for c in s.cookies:
        if c.name == "cart":
            return c.value
    return None


def _direct_add(s, variant_id):
    for attempt in range(8):
        r = s.post(
            f"{BASE}/cart/add.js",
            data={"id": variant_id, "quantity": 1},
            timeout=30,
        )
        if r.status_code == 200:
            save_cookies()
            return r.json()
        if r.status_code in (429, 430):
            time.sleep(min(3.0 * (2 ** attempt), 45.0))
            continue
        raise RuntimeError(f"add {variant_id}: HTTP {r.status_code}")
    raise RuntimeError(f"add {variant_id}: still rate-limited")


def add_variants_in_session(items):
    s = get_session()
    seen = {str(i["variant_id"]) for i in cart_contents().get("items", [])}
    added = 0
    for it in items:
        if str(it["variant_id"]) in seen:
            continue
        try:
            _direct_add(s, it["variant_id"])
            added += 1
            seen.add(str(it["variant_id"]))
        except RuntimeError as e:
            print(f"  skip: {e}")
            continue
        time.sleep(4.0)
    return added


def clear_session_cart():
    s = get_session()
    items = list(cart_contents().get("items", []))
    for line in items:
        key = line.get("key")
        if not key:
            print(f"  skip untagged cart item: {line.get('title', '?')!r}")
            continue
        for attempt in range(8):
            r = s.post(
                f"{BASE}/cart/change.js",
                data={"id": key, "quantity": 0},
                timeout=30,
            )
            if r.status_code == 200:
                save_cookies()
                break
            if r.status_code in (429, 430):
                time.sleep(min(3.0 * (2 ** attempt), 45.0))
                continue
            raise RuntimeError(f"clear {key!r}: HTTP {r.status_code}")
        else:
            raise RuntimeError(f"clear {key!r}: still rate-limited")
        time.sleep(1.0)
    return len(items)