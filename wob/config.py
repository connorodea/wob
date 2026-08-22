"""Typed configuration and environment validation (Milestone 0).

All config is read from env vars or ~/.config/wob/.env; no defaults
that hide missing required keys. Secrets are validated for presence only
(never their values). The `load()` function returns a validated Config
dataclass or raises SystemExit with a helpful message.
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import sys


@dataclasses.dataclass
class Config:
    # --- wob account (optional at load time; login enforces) ---
    wob_email: str = ""
    wob_password: str = ""

    # --- optional provider keys ---
    scrapingbee_api_key: str = ""
    ebay_app_id: str = ""
    ebay_access_token: str = ""
    dataforseo_login: str = ""
    dataforseo_password: str = ""

    # --- runtime ---
    data_dir: pathlib.Path = dataclasses.field(
        default_factory=lambda: pathlib.Path.home() / ".local" / "share" / "wob" / "data"
    )
    min_off_default: float = 0.70
    polite_wait_lo: float = 0.25
    polite_wait_hi: float = 0.60

    def __post_init__(self):
        self.data_dir = pathlib.Path(self.data_dir)  # ensure Path
        if self.min_off_default < 0 or self.min_off_default > 1:
            raise SystemExit("wob: min_off_default must be in [0,1]")

    @property
    def has_wob_creds(self) -> bool:
        return bool(self.wob_email and self.wob_password)

    @property
    def has_dataforseo_creds(self) -> bool:
        return bool(self.dataforseo_login and self.dataforseo_password)

    @property
    def has_ebay_creds(self) -> bool:
        return bool(self.ebay_app_id and self.ebay_access_token)

    @classmethod
    def load(cls, strict_creds: bool = False) -> Config:
        return load_config(strict_creds=strict_creds)


ENV_FILE = pathlib.Path.home() / ".config" / "wob" / ".env"
ALT_ENV = pathlib.Path.home() / ".claude" / "skills" / "seo" / ".env"


def _read_env():
    env = dict(os.environ)
    for path in (ENV_FILE, ALT_ENV):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def load_config(strict_creds: bool = False) -> Config:
    env = _read_env()
    wob_email = env.get("WOB_EMAIL", "").strip()
    wob_password = env.get("WOB_PASSWORD", "").strip()
    if strict_creds and (not wob_email or not wob_password):
        print(
            f"wob: WOB_EMAIL and WOB_PASSWORD are required in {ENV_FILE} or environment",
            file=sys.stderr,
        )
        sys.exit(1)

    return Config(
        wob_email=wob_email,
        wob_password=wob_password,
        scrapingbee_api_key=env.get("SCRAPINGBEE_API_KEY", "").strip(),
        ebay_app_id=env.get("EBAY_APP_ID", "").strip(),
        ebay_access_token=env.get("EBAY_ACCESS_TOKEN", "").strip(),
        dataforseo_login=env.get("DATAFORSEO_LOGIN", "").strip(),
        dataforseo_password=env.get("DATAFORSEO_PASSWORD", "").strip(),
        data_dir=env.get(
            "WOB_DATA_DIR", str(pathlib.Path.home() / ".local" / "share" / "wob" / "data")
        ),
        min_off_default=float(env.get("WOB_MIN_OFF", "0.70")),
    )
