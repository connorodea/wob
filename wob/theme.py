"""Terminal theme — a modern-academy aesthetic in the spirit of uv,
Modal, and Claude Code: one bright accent, thin rules, rounded frames,
dim hints, aligned figures. No ornamentation for its own sake.

- 256-color when TERM=xterm-256color, basic ANSI otherwise.
- Everything auto-disables when stdout is not a TTY (pipelines stay clean).
- WOB_COLOR=1 forces color; NO_COLOR kills it.
"""

import os
import sys

_RESET = "\033[0m"

_BASIC = {
    "accent": 36, "ok": 32, "gold": 33, "dim": 37,
    "hi": 37, "warn": 33, "rose": 31,
}
_256 = {
    "accent": 45, "ok": 42, "gold": 214, "dim": 240,
    "hi": 255, "warn": 178, "rose": 203,
}
_STYLES = {"bold": 1, "dim": 2, "italic": 3, "underline": 4}

_ENABLED = None


def enabled():
    global _ENABLED
    if _ENABLED is None:
        if os.environ.get("NO_COLOR"):
            _ENABLED = False
        elif os.environ.get("WOB_COLOR") == "1":
            _ENABLED = True
        else:
            _ENABLED = bool(getattr(sys.stdout, "isatty", lambda: False)())
    return _ENABLED


def _palette():
    return _256 if enabled() and os.environ.get("TERM", "").endswith("256color") else _BASIC


def paint(text, *styles):
    if not enabled() or not styles:
        return text
    codes = []
    for s in styles:
        if s in _STYLES:
            codes.append(str(_STYLES[s]))
        elif s in _palette():
            codes.append(f"38;5;{_palette()[s]}")
    if not codes:
        return text
    return f"\033[{';'.join(codes)}m{text}{_RESET}"


def bold(t):
    return paint(t, "bold")


def dim(t):
    return paint(t, "dim")


def italic(t):
    return paint(t, "italic")


# --- structure -------------------------------------------------------------

def frame(title, body, width=72):
    """Claude-Code style rounded frame.

    ╭─ title ──────────────╮
    │ body line            │
    ╰──────────────────────╯
    """
    cols = min(width, _term_cols() - 2)
    inner = cols - 2
    label = f"─ {title} " if title else "─"
    top = f"╭{label}{'─' * max(0, inner - len(label))}╮"
    lines = []
    for raw in body.splitlines():
        lines.append(f"│ {raw}{' ' * max(0, inner - len(raw) - 1)}│")
    bot = f"╰{'─' * inner}╯"
    top, bot = paint(top, "dim"), paint(bot, "dim")
    return "\n".join([top, *lines, bot])


def section(title):
    """uv-style section head:  ▸ Title  ──────────────────"""
    cols = _term_cols() - 1
    t = paint(f"▸ {title}", "accent", "bold")
    rest = cols - len(title) - 4
    return f"{t} " + paint("─" * max(0, rest), "dim") if enabled() else f"▸ {title}"


def status(mark, text, tone="ok"):
    """✓ / ✗ / • prefix like Claude Code status rows."""
    glyphs = {"ok": "✓", "err": "✗", "info": "•", "star": "✦"}
    g = paint(glyphs[mark], {"ok": "ok", "err": "rose", "info": "dim", "star": "gold"}[mark])
    return f"  {g} {text}"


def progress(frac, width=24):
    n = max(0, min(width, round(frac * width)))
    bar = "█" * n + "░" * (width - n)
    pct = paint(f"{frac*100:3.0f}%", "accent")
    return paint(bar, "accent") + " " + pct


def rule():
    cols = _term_cols() - 1
    return paint("─" * cols, "dim")


def _term_cols():
    try:
        return os.get_terminal_size().columns or 80
    except OSError:
        return 80


# --- data glyphs -----------------------------------------------------------

def site_tag(site):
    site = (site or "").replace("local:", "")
    tone = {"wob": "accent", "tb": "warn"}.get(site, "dim")
    return paint(f"[{site}]", tone)


def money(v, positive=False):
    if v is None:
        return paint("      —", "dim")
    s = f"${v:>7.2f}"
    return paint(s, "ok", "bold") if positive else paint(s, "hi")


def pct_colored(p):
    if p is None:
        return paint("    — ", "dim")
    s = f"{p*100:5.1f}%"
    tone = "gold" if p >= 0.90 else "ok" if p >= 0.80 else "hi" if p >= 0.70 else "dim"
    return paint(s, tone, "bold" if p >= 0.90 else None)


def cond_badge(cond):
    tone = {
        "NEW": "ok", "LIKE_NEW": "accent", "VERY_GOOD": "hi",
        "GOOD": "warn", "WELL_READ": "gold", "ACCEPTABLE": "rose",
    }.get(cond, "dim")
    return paint(f"{cond:>10}", tone)


def q_star(quality):
    return paint("✦", "gold", "bold") if quality else " "


def score_bar(score, width=10):
    n = max(0, min(width, round(score / 1.2 * width)))
    bar = "▮" * n + "▯" * (width - n)
    return paint(bar, "gold")


def hint(text):
    return paint(text, "dim")


def whisper(text):
    """One dim closing line."""
    return paint(text, "dim")