import subprocess
import sys

import pytest

from memebot.core.instance import InstanceAlreadyRunning, instance_lock


def test_duplicate_rejected_roles_independent_and_release(tmp_path):
    with instance_lock("discover", directory=tmp_path):
        with pytest.raises(InstanceAlreadyRunning):
            with instance_lock("discover", directory=tmp_path):
                pytest.fail("Duplicate entered")
        with instance_lock("telegram", directory=tmp_path):
            pass
    with instance_lock("discover", directory=tmp_path):
        pass


def test_crashed_process_releases_lock(tmp_path):
    program = (
        "import os, sys; from pathlib import Path; "
        "from memebot.core.instance import instance_lock; "
        "guard = instance_lock('discover', directory=Path(sys.argv[1])); "
        "guard.__enter__(); print('locked', flush=True); "
        "sys.stdin.readline(); os._exit(7)"
    )
    child = subprocess.Popen(
        [sys.executable, "-u", "-c", program, str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout.readline().strip() == "locked"
        with pytest.raises(InstanceAlreadyRunning):
            with instance_lock("discover", directory=tmp_path):
                pytest.fail("Duplicate entered")
        child.communicate("exit\n", timeout=10)
        assert child.returncode == 7
        with instance_lock("discover", directory=tmp_path):
            pass
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=10)
