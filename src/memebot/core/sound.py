"""Fire-and-forget local sound playback (Windows MCI; no extra dependency)."""

from __future__ import annotations

import sys
import threading
from itertools import count
from pathlib import Path

from memebot.core.logging import get_logger

_aliases = count()


def play_sound(path: Path, volume_percent: int = 100) -> None:
    """Play an mp3/wav without blocking. Silently does nothing off Windows."""
    if sys.platform != "win32" or not path.is_file():
        return
    threading.Thread(target=_play, args=(path, volume_percent), daemon=True, name="sound").start()


def _play(path: Path, volume_percent: int) -> None:
    import ctypes

    mci = ctypes.windll.winmm.mciSendStringW
    alias = f"bullseye{next(_aliases)}"
    try:
        if mci(f'open "{path}" type mpegvideo alias {alias}', None, 0, None) != 0:
            return
        mci(f"setaudio {alias} volume to {volume_percent * 10}", None, 0, None)
        mci(f"play {alias} wait", None, 0, None)
    except OSError:
        get_logger("memebot.sound").warning("sound_playback_failed")
    finally:
        mci(f"close {alias}", None, 0, None)
