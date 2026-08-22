"""Structured logging (Milestone 0) — stdlib logging + a JSONL event sink.

The JSONL sink writes one event per line to WOB_LOG_FILE (default
data/logs/events.jsonl) when WOB_LOG_JSON=1 or when a sink path is set.
Plain stderr logging remains the default (keeps scan output clean).
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import time

LOGGER = logging.getLogger("wob")
_JSON_SINK = None


def _sink_path():
    p = os.environ.get("WOB_LOG_FILE")
    if p:
        return pathlib.Path(p)
    return None


def enable_json_sink():
    """Write every wob log event as one JSON line (append-only)."""
    global _JSON_SINK
    path = _sink_path()
    if path is None:
        path = pathlib.Path.home() / ".local" / "share" / "wob" / "data" / "logs" / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    _JSON_SINK = path
    return path


def _emit(record):
    if _JSON_SINK is None:
        return
    try:
        with open(_JSON_SINK, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": time.time(),
                "level": record.levelname.lower(),
                "logger": record.name,
                "msg": record.getMessage(),
                "name": getattr(record, "event", None),
                "extra": getattr(record, "data", None),
            }, default=str) + "\n")
    except OSError:
        pass  # logging must never crash the pipeline


class JsonHandler(logging.Handler):
    def emit(self, record):
        _emit(record)


def setup(level=logging.INFO):
    if not LOGGER.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        LOGGER.addHandler(h)
    LOGGER.setLevel(level)
    if os.environ.get("WOB_LOG_JSON") == "1":
        LOGGER.addHandler(JsonHandler())
    return LOGGER


def event(name, data=None, level=logging.INFO):
    LOGGER.log(level, name, extra={"event": name, "data": data or {}})  # noqa: G003