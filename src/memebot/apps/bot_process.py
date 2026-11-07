"""Start and stop the PAPER bot console from Telegram (one instance only)."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from memebot.core.instance import InstanceAlreadyRunning, instance_lock

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / ".runtime"
STOP_REQUEST_NAME = "stop.request"
# Same command Vlad runs by hand (docs/STARTUP.md); stderr log stays in the file.
BOT_COMMAND = (
    'cmd /c "title Bullseye bot & .venv\\Scripts\\python.exe -u '
    'analysis\\run_operational_paper.py --continuous 2> analysis\\paper_run.err.log"'
)


def bot_running(directory: Path | None = None) -> bool:
    """True while a bot process holds the discovery lock."""
    try:
        with instance_lock("discover", directory=directory or RUNTIME):
            return False
    except InstanceAlreadyRunning:
        return True


def archive_previous_log(root: Path = ROOT) -> Path | None:
    """Keep the last run's log (insider_facts etc.); the start command truncates it."""
    log = root / "analysis" / "paper_run.err.log"
    if not log.exists() or log.stat().st_size == 0:
        return None
    stamp = datetime.fromtimestamp(log.stat().st_mtime).strftime("%Y%m%d-%H%M%S")
    target = root / "analysis" / "logs" / f"paper_run_{stamp}.err.log"
    target.parent.mkdir(parents=True, exist_ok=True)
    log.replace(target)
    return target


def start_bot_console() -> subprocess.Popen[bytes]:
    """Open the bot in its own console window, exactly like the manual start."""
    clear_stop_request()
    archive_previous_log()
    flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    return subprocess.Popen(BOT_COMMAND, cwd=ROOT, creationflags=flags)


def stop_request_path(directory: Path | None = None) -> Path:
    return (directory or RUNTIME) / STOP_REQUEST_NAME


def request_stop(directory: Path | None = None) -> None:
    path = stop_request_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stop", encoding="utf-8")


def clear_stop_request(directory: Path | None = None) -> None:
    stop_request_path(directory).unlink(missing_ok=True)


def stop_requested(directory: Path | None = None) -> bool:
    return stop_request_path(directory).exists()
