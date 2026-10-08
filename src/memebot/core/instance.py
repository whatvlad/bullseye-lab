"""OS-owned locks: a crashed process cannot leave a stale PID lock behind."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal


class InstanceAlreadyRunning(RuntimeError):
    pass


@contextmanager
def instance_lock(
    role: Literal["discover", "telegram"], *, directory: Path | None = None
) -> Iterator[None]:
    root = directory if directory is not None else Path(__file__).resolve().parents[3] / ".runtime"
    root.mkdir(parents=True, exist_ok=True)
    # Keep the same inode/path across starts; never unlink a potentially held lock.
    with (root / f"{role}.lock").open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise InstanceAlreadyRunning(f"{role} is already running in this project") from error
        try:
            yield
        finally:
            handle.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
