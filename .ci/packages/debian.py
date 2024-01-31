#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
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


def _python():
    _path = pathlib.Path("python").resolve(strict = True)
    assert _path.is_dir()
    _path, = _path.glob("*.tar.*")
    assert _path == _path.resolve(strict=True)
    assert _path.is_file()
    _name, _version = _path.name.split("-")
    assert _name == _name.strip()
    _name, = _name.splitlines()
    _version = list(_version.split(".tar."))
    assert "." not in _version.pop(1)
    _version, = _version
    assert _version
    assert _version == _version.strip()
    _version, = _version.splitlines()
    return dict(name = _name, version = _version, path = _path.as_posix())


_python = _python()
_destination = pathlib.Path("debian")
_destination.mkdir(parents = False, exist_ok = False)
_destination = _destination.resolve(strict = True)
assert _destination.is_dir()

with tempfile.TemporaryDirectory(dir = _destination, prefix = "tmp.") as _temporary:
    _temporary = pathlib.Path(_temporary)
    assert _temporary.resolve(strict = True) == _temporary
    assert _temporary.is_dir()

    def _prepare():
        _source = _python["path"]
        assert isinstance(_source, str)
        _source = pathlib.Path(_source)
        assert _source.is_absolute()
        _source = _source.resolve(strict = True)
        assert _source.is_file()

        _path = _temporary / "working"
        _path.mkdir(parents = False, exist_ok = False)
        assert _path.resolve(strict = True) == _path
        assert _path.is_dir()
        subprocess.check_call((
            "tar", "--extract", f"--file={_source.as_posix()}"
        ), cwd = _path)
        _working, = _path.glob("*")
        assert _working.name == "-".join((_python["name"], _python["version"]))
        _path = _working / "setup.py"
        assert _path.resolve(strict = False) == _path
        assert not _path.exists()
        with open(_path, "w") as _stream: print("""
from setuptools import setup
if "__main__" == __name__: setup(url = "https://github.com/p5-vbnekit/lcboot")
        """.strip(), file = _stream)
        _path = _path.parent
        _source = _temporary / "source.tar.gz"
        assert _source.resolve(strict = False) == _source
        assert not _source.exists()
        subprocess.check_call((
            "tar", "--create", "--gzip", f"--file={_source.as_posix()}", "--", _path.name
        ), cwd = _path.parent)
        _path = _path.parent
        shutil.rmtree(_path)
        _path.mkdir(parents = False, exist_ok = False)
        subprocess.check_call((
            "py2dsc", "--compat=13", "--maintainer=p5-vbnekit <vbnekit@gmail.com>",
            f"--dist-dir=.", "--", _source.as_posix()
        ), cwd = _path)
        _source.unlink()
        return _path

    def _build():
        _path = _prepare()

        _upstream_name = _python["name"]
        _upstream_version = _python["version"]

        _dash_name = _upstream_name.replace(".", "-")
        _binary_name = f"python3-{_upstream_name}"

        _path, = filter(lambda path: path.is_dir(), _path.glob("*"))
        assert _path.resolve(strict = True) == _path
        assert _path.name == "-".join((_dash_name, _upstream_version))

        with open(_path / "debian/control", "r") as _control: _control = _control.read()
        assert _control

        with open(_path / "debian/control", "w") as _stream:
            for _control in _control.splitlines():
                if _control.startswith("Build-Depends: "): _control = _control.replace("debhelper (>= 9)", "debhelper (>= 13)")
                print(_control, file = _stream)

        with open(_path / "debian/copyright", "w") as _stream: print(f"""
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: {_dash_name}
Upstream-Contact: p5-vbnekit <vbnekit@gmail.com>

Files: *
Copyright: public-domain
License: public-domain

License: public-domain
  The work is in the public domain. To the extent permitted by law, no
  copyrights apply.
        """.strip(), file = _stream)

        with open(_path / f"debian/{_binary_name}.lintian-overrides", "w") as _stream: print("\n".join((
            "no-manual-page",
            "initial-upload-closes-no-bugs",
            "extended-description-line-too-long",
            "possible-unindented-list-in-extended-description"
        )), file = _stream)

        subprocess.check_call(("debuild", "-uc", "-us"), cwd = _path)

        shutil.rmtree(_path)
        _path.mkdir(parents = False, exist_ok = False)

        _archive, = _path.parent.glob(f"{_dash_name}_{_upstream_version}.orig.tar.*")
        assert _archive.resolve(strict = True) == _archive
        assert _archive.is_file()
        subprocess.check_call(("tar", "--extract", f"--file={_archive.as_posix()}"), cwd = _path)
        _path, = _path.glob("*")
        assert _path.resolve(strict = True) == _path
        assert _path.is_dir()
        if _path.name != _path.parent.name:
            _path.replace(_path.parent / _path.parent.name)
            _path = _path.parent / _path.parent.name
        _archive = ".".join(_archive.name.split(".")[:-1])
        assert _archive
        _archive = _destination / _archive
        subprocess.check_call((
            "tar", "--create", f"--file={_archive.as_posix()}", "--", f"./{_path.name}"
        ), cwd = _path.parent)
        subprocess.check_call((
            "xz", "-9", "--", f"./{_archive.name}"
        ), cwd = _archive.parent)
        shutil.rmtree(_path)
        _path = _path.parent

        _archive, = _path.parent.glob(f"{_dash_name}_{_upstream_version}-1.debian.tar.*")
        assert _archive.resolve(strict = True) == _archive
        assert _archive.is_file()
        subprocess.check_call(("tar", "--extract", f"--file={_archive.as_posix()}"), cwd = _path)
        _path, = _path.glob("*")
        assert _path.name == "debian"
        assert _path.resolve(strict = True) == _path
        assert _path.is_dir()
        _archive = ".".join(_archive.name.split(".")[:-1])
        assert _archive
        _archive = _destination / _archive
        subprocess.check_call((
            "tar", "--create", f"--file={_archive.as_posix()}", "--", f"./{_path.name}"
        ), cwd = _path.parent)
        subprocess.check_call((
            "xz", "-9", "--", f"./{_archive.name}"
        ), cwd = _archive.parent)
        _path = _path.parent
        shutil.rmtree(_path)

        _path = _path.parent / f"{_binary_name}_{_upstream_version}-1_all.deb"
        assert _path.resolve(strict = True) == _path
        assert _path.is_file()
        _path.replace(_destination / _path.name)


    _build()
