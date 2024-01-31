#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shlex
import shutil
import pathlib
import subprocess

assert "__main__" == __name__

_stdin = sys.stdin
if _stdin is not None:
    _stdin = [_stdin.fileno(), _stdin]
    _stdin.pop().close()
    os.close(_stdin.pop())
del _stdin

assert 0 == os.getuid()
assert 0 == os.getgid()
assert 0 == os.geteuid()
assert 0 == os.getegid()

_current_directory = pathlib.Path(".").resolve(strict = True)

_snapshot_directory = pathlib.Path(__file__).resolve(strict = True)
assert _snapshot_directory.is_file()
_snapshot_directory = _snapshot_directory.parent.parent

pathlib.Path("/etc/apt/sources.list").unlink(missing_ok = True)
shutil.rmtree("/etc/apt/sources.list.d")
pathlib.Path("/etc/apt/sources.list.d").mkdir(parents = False, exist_ok = False)

with open("/etc/apt/sources.list.d/debian.sources", "w") as _stream: print("""
Types: deb deb-src
URIs: http://deb.debian.org/debian
Suites: bookworm bookworm-updates bookworm-proposed-updates bookworm-backports bookworm-backports-sloppy
Components: main contrib non-free non-free-firmware

Types: deb deb-src
URIs: http://deb.debian.org/debian-security
Suites: bookworm-security
Components: main contrib non-free non-free-firmware
""".strip(), file = _stream)


def _shell(script: str, user = None, group = None):
    assert isinstance(script, str)
    if str is not type(script): script = str(script)
    script = script.strip()
    assert script
    assert 0 == subprocess.run(
        ("/bin/sh", "-xe"), input = f"{script}\n".encode("ascii"),
        user = user, group = group
    ).returncode


_quoted_current_directory = shlex.quote(_current_directory.as_posix())
_quoted_snapshot_directory = shlex.quote(_snapshot_directory.as_posix())

_shell(script = f"""
    apt update --assume-yes
    apt-mark showmanual | xargs --no-run-if-empty -- apt-mark auto --
    apt install --assume-yes apt-utils
    apt install --assume-yes git gcc xz-utils devscripts debootstrap guestfs-tools
    apt install --assume-yes python3-venv python3-build python3-stdeb
    apt install --assume-yes dh-python libpython3-dev libapt-pkg-dev
    apt full-upgrade --assume-yes
    apt autoremove --assume-yes
    apt purge --assume-yes '~c'

    adduser \
      --disabled-login --disabled-password --no-create-home \
      --home={_quoted_current_directory} --shell=/bin/false --gecos "" \
    -- build

    chown --recursive build:build -- {_quoted_current_directory} {_quoted_snapshot_directory}
""")


def _resolve_script(name: str):
    assert isinstance(name, str)
    if str is not type(name): name = str(name)
    assert name
    _path = _snapshot_directory / f".ci/{name}.py"
    assert _path.resolve(strict = True) == _path
    return _path.as_posix()


_shell(script = f"""
    export HOME={_quoted_current_directory}

    {shlex.quote(sys.executable)} -m venv --system-site-packages -- ./venv
    venv/bin/python -m pip install --upgrade pip
    venv/bin/pip install --upgrade pyproject-flake8
    venv/bin/pip install --upgrade git+https://salsa.debian.org/apt-team/python-apt.git@2.7.5

    venv/bin/python {shlex.quote(_resolve_script(name = "inspect"))}
    venv/bin/python {shlex.quote(_resolve_script(name = "packages"))}
    venv/bin/python {shlex.quote(_resolve_script(name = "mount-idmapped"))}
""", user = "build", group = "build")

subprocess.check_call(("venv/bin/python", _resolve_script(name = "image")))
