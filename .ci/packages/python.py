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

_path = pathlib.Path("python")
_path.mkdir(parents = False, exist_ok = False)
_path = _path.resolve(strict = True)
assert _path.is_dir()

_snapshot = pathlib.Path(__file__).resolve(strict = True)
assert _snapshot.is_file()
_snapshot = _snapshot.parent.parent.parent
assert _snapshot.is_dir()
subprocess.check_call((
    sys.executable, "-m", "build", "--sdist", f"--outdir={_path.as_posix()}", "--", _snapshot.as_posix()
))
