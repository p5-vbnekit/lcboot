#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pathlib
import subprocess

assert "__main__" == __name__

_interpreter = pathlib.Path(sys.executable).resolve(strict = True)
assert _interpreter.is_file()
_interpreter = _interpreter.as_posix()

_build_directory, _snapshot_directory = sys.argv[1:]

assert _build_directory
_build_directory = pathlib.Path(_build_directory)
_build_directory.mkdir(parents = True, exist_ok = True)
_build_directory = _build_directory.resolve(strict = True)
assert _build_directory.is_dir()

assert _snapshot_directory
_snapshot_directory = pathlib.Path(_snapshot_directory).resolve(strict = True)
assert _snapshot_directory.is_dir()

_uid = _snapshot_directory.stat()
_uid, _gid = _uid.st_uid, _uid.st_gid
assert isinstance(_uid, int) and (0 <= _uid)
assert isinstance(_gid, int) and (0 <= _gid)

_script_path = _snapshot_directory / ".ci/bookworm.py"
assert _script_path.resolve(strict = True) == _script_path
assert _script_path.is_file()
_script_path = _script_path.as_posix()

try: subprocess.check_call((_interpreter, _script_path), cwd = _build_directory)
finally: subprocess.check_call((
    "chown", "--recursive", f"{_uid}:{_gid}", "--",
    _build_directory.as_posix(),
    _snapshot_directory.as_posix()
))
