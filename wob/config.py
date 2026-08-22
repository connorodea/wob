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
from typing import Optional


@dataclasses.dataclass
class Config:
    # --- required ---
    wob_email: str
    wob_password: str

    # --- optional ---
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

    _HOME: dataclasses.InitVar = pathlib.Path()

    def __post_init__(self):
        self.data_dir = pathlib.Path(self.data_dir)  # ensure Path
        if self.min_off_default < 0 or self.min_off_default > 1:
            raise SystemExit("wob: min_off_default must be in [0,1]")

    @classmethod
    def load(cls) -> Config:
        return load_config()


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


def load_config() -> Config:
    env = _read_env()
    wob_email = env.get("WOB_EMAIL", "").strip()
    wob_password = env.get("WOB_PASSWORD", "").strip()
    if not wob_email or not wob_password:
        print("wob: WOB_EMAIL and WOB_PASSWORD are required in "
              f"{ENV_FILE} or environment", file=sys.stderr)
        sys.exit(1)

    return Config(
        wob_email=wob_email,
        wob_password=wob_password,
        scrapingbee_api_key=env.get("SCRAPINGBEE_API_KEY", "").strip(),
        ebay_app_id=env.get("EBAY_APP_ID", "").strip(),
        ebay_access_token=env.get("EBAY_ACCESS_TOKEN", "").strip(),
        dataforseo_login=env.get("DATAFORSEO_LOGIN", "").strip(),
        dataforseo_password=env.get("DATAFORSEO_PASSWORD", "").strip(),
        data_dir=env.get("WOB_DATA_DIR",
                         str(pathlib.Path.home() / ".local" / "share" / "wob" / "data")),
        min_off_default=float(env.get("WOB_MIN_OFF", "0.70")),
    )