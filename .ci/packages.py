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

_destination = pathlib.Path("packages")
_destination.mkdir(parents = False, exist_ok = False)
_destination = _destination.resolve(strict = True)
assert _destination.is_dir()


def _call_script(name: str):
    assert isinstance(name, str)
    if str is not type(name): name = str
    assert name
    _path = _snapshot / ".ci/packages" / f"{name}.py"
    assert _path.resolve(strict = True) == _path
    assert _path.is_file()
    subprocess.check_call((sys.executable, _path.as_posix()), cwd = _destination)


for _name in ("python", "debian"): _call_script(name = _name)
