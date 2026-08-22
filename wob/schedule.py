import os
import pathlib
import plistlib
import re
import subprocess

LAUNCH_DIR = pathlib.Path.home() / "Library" / "LaunchAgents"
PROJECT_DIR = pathlib.Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_DIR / "data" / "logs"
BIN = pathlib.Path.home() / ".local" / "bin" / "wob"

NAME_RE = re.compile(r"^[a-z0-9_-]+$")


def _label(name):
    return f"com.connorodea.wob-scan.{name}"


def _plist_path(name):
    return LAUNCH_DIR / f"{_label(name)}.plist"


def _target():
    return f"gui/{os.getuid()}"


def add(name, keywords, every_hours, sites, min_off, max_hits, pages):
    if not NAME_RE.match(name):
        raise SystemExit(f"bad name {name!r}: use letters, digits, - and _ only")
    if every_hours < 0.25:
        raise SystemExit(f"--every too small ({every_hours}h): minimum is 0.25h (15 min)")
    kw = pathlib.Path(keywords).resolve()
    if not kw.exists():
        raise SystemExit(f"keywords file not found: {kw}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    pl = {
        "Label": _label(name),
        "ProgramArguments": [
            str(BIN),
            "scan",
            "--keywords",
            str(kw),
            "--sites",
            sites,
            "--min-off",
            str(min_off),
            "--max-hits",
            str(max_hits),
            "--pages",
            str(pages),
        ],
        "StartInterval": int(every_hours * 3600),
        "RunAtLoad": False,
        "WorkingDirectory": str(PROJECT_DIR),
        "StandardOutPath": str(LOG_DIR / f"{name}.log"),
        "StandardErrorPath": str(LOG_DIR / f"{name}.err.log"),
    }
    path = _plist_path(name)
    path.write_bytes(plistlib.dumps(pl))
    subprocess.run(["launchctl", "bootout", f"{_target()}/{_label(name)}"], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", _target(), str(path)], check=True)
    print(f"scheduled {name!r}: every {every_hours}h, sites={sites}, keywords={kw.name}")


def list_jobs():
    found = False
    for pl in sorted(LAUNCH_DIR.glob("com.connorodea.wob-scan.*.plist")):
        found = True
        name = pl.stem.replace("com.connorodea.wob-scan.", "")
        r = subprocess.run(
            ["launchctl", "print", f"{_target()}/{_label(name)}"],
            capture_output=True,
            text=True,
        )
        state = "loaded" if r.returncode == 0 else "missing"
        print(f"  {name}  [{state}]  {pl}")
    if not found:
        print("no wob schedules installed")
    return found


def remove(name):
    if not NAME_RE.match(name):
        raise SystemExit(f"bad name {name!r}")
    subprocess.run(["launchctl", "bootout", f"{_target()}/{_label(name)}"], capture_output=True)
    path = _plist_path(name)
    if path.exists():
        path.unlink()
        print(f"removed {name!r}")
    else:
        print(f"no schedule named {name!r}")


def run_now(name):
    subprocess.run(
        ["launchctl", "kickstart", f"{_target()}/{_label(name)}"], check=True
    )
    print(f"kicked {name!r} (log: data/logs/{name}.log)")