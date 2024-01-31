#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import pathlib
import tempfile
import subprocess

assert "__main__" == __name__

_stdin = sys.stdin
if _stdin is not None:
    _stdin = [_stdin.fileno(), _stdin]
    _stdin.pop().close()
    os.close(_stdin.pop())
del _stdin

_name = "mount-idmapped"

_destination = pathlib.Path(".").resolve(strict = True)
assert _destination.is_dir()

with tempfile.TemporaryDirectory(dir = _destination, prefix = f"{_name}.src.tmp.") as _temporary:
    _source = pathlib.Path(_temporary)
    assert _source.resolve(strict = True) == _source
    assert _source.is_dir()

    _source = _source / "src"
    assert not (_source.is_symlink() or _source.exists())

    subprocess.check_call((
        "git", "clone", "--depth=1", "--", f"https://github.com/brauner/{_name}.git", _source.as_posix()
    ), cwd = _destination)
    assert _source.resolve(strict = True) == _source
    assert _source.is_dir()
    _source = _source / f"{_name}.c"
    assert _source.resolve(strict = True) == _source
    assert _source.is_file()

    _destination = _destination / _name
    assert not (_destination.is_symlink() or _destination.exists())

    subprocess.check_call((
        "gcc", "-g0", "-O3", "-DNDEBUG", f"-o{_destination.as_posix()}", _source.as_posix()
    ))
