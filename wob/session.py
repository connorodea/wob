import http.cookiejar
import pathlib
import random
import time

import requests

CONFIG_DIR = pathlib.Path.home() / ".config" / "wob"
ENV_FILE = CONFIG_DIR / ".env"
JAR_FILE = CONFIG_DIR / "jar.txt"

BASE = "https://www.worldofbooks.com"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_session = None


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_session():
    global _session
    if _session is not None:
        return _session
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    jar = http.cookiejar.MozillaCookieJar(str(JAR_FILE))
    if JAR_FILE.exists():
        jar.load(ignore_discard=True, ignore_expires=True)
    s.cookies = jar
    _session = s
    return s


def save_cookies():
    get_session().cookies.save(ignore_discard=True, ignore_expires=True)


def fetch(url, method="GET", data=None, headers=None, fallback_render=False):
    s = get_session()
    attempt = 0
    while True:
        attempt += 1
        try:
            r = s.request(method, url, data=data, headers=headers, timeout=35)
        except requests.RequestException:
            if attempt <= 3:
                time.sleep(1.5 * attempt + random.random())
                continue
            raise
        if r.status_code in (429, 430, 403):
            if method != "GET":
                raise RuntimeError(
                    f"blocked {r.status_code} on {method} {url} - "
                    "ScrapingBee fallback only replays GET"
                )
            return _fetch_via_scrapingbee(url, render=fallback_render)
        if r.status_code >= 500 and attempt <= 3:
            time.sleep(2.0 * attempt + random.random())
            continue
        r.raise_for_status()
        return r


def _fetch_via_scrapingbee(url, render=False):
    env = load_env()
    key = env.get("SCRAPINGBEE_API_KEY") or __import__("os").environ.get(
        "SCRAPINGBEE_API_KEY"
    )
    if not key:
        raise RuntimeError("request blocked and no SCRAPINGBEE_API_KEY available")
    params = {"api_key": key, "url": url, "country_code": "us", "timeout": 30000}
    if render:
        params["render_js"] = "true"
    try:
        r = requests.get("https://app.scrapingbee.com/api/v1/", params=params, timeout=90)
        r.raise_for_status()
    except requests.RequestException as e:
        # never let the API key appear in error text
        raise RuntimeError(f"ScrapingBee fallback failed ({e.response.status_code if e.response is not None else 'network'})") from None
    from types import SimpleNamespace

    return SimpleNamespace(text=r.text, content=r.content, status_code=r.status_code)


def polite_wait(lo=0.25, hi=0.6):
    time.sleep(random.uniform(lo, hi))


def login():
    env = load_env()
    fetch(
        f"{BASE}/account/login",
        method="POST",
        data={
            "form_type": "customer_login",
            "utf8": "\u2713",
            "customer[email]": env["WOB_EMAIL"],
            "customer[password]": env["WOB_PASSWORD"],
        },
        headers={"Referer": f"{BASE}/account/login"},
    )
    save_cookies()
    return logged_in()


def logged_in():
    r = fetch(f"{BASE}/account", headers={"Accept": "text/html"})
    return "logout" in r.text.lower()