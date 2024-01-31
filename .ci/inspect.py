#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import pathlib
import subprocess

assert "__main__" == __name__

_stdin = sys.stdin
if _stdin is not None:
    _stdin = [_stdin.fileno(), _stdin]
    _stdin.pop().close()
    os.close(_stdin.pop())
del _stdin

_snapshot = pathlib.Path(__file__).resolve(strict = True)
assert _snapshot.is_file()
_snapshot = _snapshot.parent.parent

_path = _snapshot / "pyproject.toml"
assert _path == _path.resolve(strict = True)
assert _path.is_file()
_command = [sys.executable, "-m", "pflake8", "--statistics", "--show-source", f"--config={_path.as_posix()}"]
_path = _snapshot / "python3"
assert _path == _path.resolve(strict = True)
assert _path.is_dir()
_command.extend(("--", _path.as_posix()))
subprocess.check_call(_command)
