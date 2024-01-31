#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shlex
import typing
import shutil
import apt_pkg
import pathlib
import tempfile
import contextlib
import subprocess

assert "__main__" == __name__

_stdin = sys.stdin
if _stdin is not None:
    _stdin = [_stdin.fileno(), _stdin]
    _stdin.pop().close()
    os.close(_stdin.pop())
del _stdin

_current = pathlib.Path(".").resolve(strict = True)
assert _current.is_dir()

_snapshot = pathlib.Path(__file__).resolve(strict = True)
assert _snapshot.is_file()
_snapshot = _snapshot.parent.parent


def _debian_path():
    _path = _current / "packages/debian"
    assert _path.resolve(strict = True) == _path
    assert _path.is_dir()
    _path, = _path.glob("python3-*_*-*_all.deb")
    assert _path.resolve(strict = True) == _path
    assert _path.is_file()
    return _path


_debian_path = _debian_path()
_debian_name = _debian_path.name.split("_")
assert "all.deb" == _debian_name.pop(-1)
_debian_version = _debian_name.pop(-1)
assert _debian_version
_debian_name, = _debian_name
assert _debian_name
_python_name = _debian_name.split("-")
assert "python3" == _python_name.pop(0)
_python_name, = _python_name
assert _python_name
_python_version = _debian_version.split("-")
assert "1" == _python_version.pop(-1)
_python_version, = _python_version
assert 3 == len(_python_version.split("."))

_destination = _current / "image"
assert _destination.resolve(strict = False) == _destination
_destination.mkdir(parents = False, exist_ok = False)
assert _destination.resolve(strict = True) == _destination
assert _destination.is_dir()

_unnecessary_paths = tuple("""
opt
media
etc/apt
etc/gss
etc/opt
etc/rmt
etc/motd
etc/fstab
etc/group
etc/pam.d
etc/init.d
etc/shells
etc/subuid
etc/subgid
etc/shadow
etc/passwd
etc/default
etc/gshadow
etc/profile
etc/inputrc
etc/systemd
etc/security
etc/hostname
etc/.pwd.lock
etc/netconfig
etc/cron.daily
etc/xattr.conf
etc/ld.so.cache
etc/resolv.conf
etc/logrotate.d
etc/environment
etc/alternatives
etc/ld.so.conf.d
etc/nsswitch.conf
etc/dpkg/origins
etc/dpkg/dpkg.cfg.d
usr/local
usr/include
usr/lib/udev
usr/lib/systemd
usr/lib/valgrind
usr/share/doc
usr/share/man
usr/share/bug
usr/share/info
usr/share/menu
usr/share/locale
usr/share/binfmts
usr/share/lintian
usr/share/doc-base
usr/share/readline
usr/share/util-linux
usr/share/debianutils
usr/share/applications
usr/share/bash-completion
usr/share/pixmaps
usr/share/polkit-1
var/log
var/opt
var/mail
var/spool
var/lib/systemd
var/lib/dpkg/alternatives
root
""".strip().splitlines(keepends = False))


@contextlib.contextmanager
def _mount_manager(bundle: pathlib.Path):
    assert isinstance(bundle, pathlib.Path)
    bundle = pathlib.Path(bundle.as_posix())
    assert bundle.resolve(strict = True) == bundle
    assert bundle.is_dir()

    _mounted = list()
    _items = ("dev", "sys", "run", "proc")

    def _bind(source: str):
        assert isinstance(source, str)
        if str is not type(source): source = str(source)
        assert source
        source = pathlib.Path(source)
        assert not source.is_absolute()
        assert source.parts[0] not in {"/", ".", ".."}
        _target = bundle / source
        assert _target == _target.resolve(strict = True)
        assert _target.is_dir()
        _target = _target.as_posix()
        source = (pathlib.Path("/") / source).resolve(strict = True)
        assert source.is_dir()
        source = source.as_posix()
        subprocess.check_call(("mount", "--rbind", "--", source, _target))
        _mounted.insert(0, _target)

    def _umount(): subprocess.check_call(("umount", "--recursive", "--", *_mounted))

    _temporary = bundle / "tmp"
    assert _temporary.resolve(strict = True) == _temporary
    assert _temporary.is_dir()
    _temporary = _temporary.as_posix()

    try:
        subprocess.check_call(("mount", "--types=tmpfs", "--", "none", _temporary))
        _mounted.append(_temporary)
        for _source in ("dev", "sys", "run", "proc"): _bind(source = _source)
        yield

    finally: _umount()


def _shell(script: str, chroot: pathlib.Path = None):
    assert isinstance(script, str)
    if str is not type(script): script = str(script)
    script = script.strip()
    assert script
    script = dict(input = f"{script}\n".encode("ascii"))
    if chroot is not None:
        assert isinstance(chroot, pathlib.Path)
        chroot = pathlib.Path(chroot.as_posix()).resolve(strict = True)
        if 1 < len(chroot.parts):
            def _chroot():
                os.chdir(chroot)
                os.chroot(chroot)
                os.chdir("/")
            script.update(preexec_fn = _chroot)
    assert 0 == subprocess.run(("/bin/sh", "-xe"), **script).returncode


def _unnecessary_packages(bundle: pathlib.Path, keep: typing.Iterable[str]):
    _keep = set()

    _database = bundle / "var/lib/dpkg/status"
    assert _database.resolve(strict = True) == _database
    assert _database.is_file()
    _database = _database.as_posix()

    def _generate_dependencies(section: apt_pkg.TagSection):
        for _key in "Depends", "Pre-Depends":
            try: _field = section[_key]
            except KeyError: continue
            _field = apt_pkg.parse_depends(_field)
            for _field in _field:
                for _dependency in _field: yield _dependency[0]

    with apt_pkg.TagFile(_database) as _dpkg_sections:
        _database = dict()
        for _dpkg_section in _dpkg_sections:
            _package = _dpkg_section["Package"]
            assert _package not in _database
            _database[_package] = tuple(_generate_dependencies(section = _dpkg_section))

    def _collect(package: str):
        if package in _keep: return
        _keep.add(package)
        try: package = _database[package]
        except KeyError: return
        for package in package: _collect(package = package)

    for keep in keep: _collect(package = keep)
    yield from filter(lambda package: package not in _keep, _database.keys())


def _remove(path: pathlib.Path):
    assert isinstance(path, pathlib.Path)
    path = pathlib.Path(path.as_posix())
    assert path.is_symlink() or path.exists()
    if path.is_symlink(): path.unlink(missing_ok = False)
    elif path.is_dir(): shutil.rmtree(path)
    else: path.unlink(missing_ok = False)


def _tar():
    with tempfile.TemporaryDirectory(dir = _destination, prefix = "tmp.") as _temporary:
        _temporary = pathlib.Path(_temporary)
        assert _temporary.resolve(strict = True) == _temporary
        assert _temporary.is_dir()
        _bundle = _temporary / "bundle"
        _bundle.mkdir(parents = False, exist_ok = False)

        subprocess.check_call(("debootstrap", "--variant=minbase", "bookworm", _bundle.as_posix()))

        _path = "etc/apt/sources.list"
        (_bundle / _path).unlink(missing_ok = True)
        _path = f"{_path}.d"
        _remove(path = _bundle / _path)
        (_bundle / _path).mkdir(parents = False, exist_ok = False)
        _path = f"{_path}/debian.sources"
        shutil.copy(f"/{_path}", _bundle / _path)

        _required_packages = _debian_name, "python3", "iproute2", "dash", "mount", "coreutils", "util-linux"
        _temporary_packages = (
            "grep", "debconf", "diffutils", "findutils",
            "libc-bin", "perl-base", "systemctl", "init-system-helpers"
        )

        with _mount_manager(bundle = _bundle):
            shutil.copy(_debian_path, _bundle / "tmp" / _debian_path.name)

            _shell(script = f"""
apt update --assume-yes
apt-mark showmanual | xargs --no-run-if-empty -- apt-mark auto --
apt install --assume-yes -- /tmp/{shlex.quote(_debian_path.name)}
apt install --assume-yes -- {" ".join([shlex.quote(_p) for _p in (*_required_packages, *_temporary_packages)])}
apt autoremove --assume-yes --allow-remove-essential --allow-change-held-packages
apt purge --assume-yes '~c'
apt full-upgrade --assume-yes
apt clean --assume-yes
            """, chroot = _bundle)

            subprocess.check_call((
                "chroot", _bundle.as_posix(), "dpkg", "--purge",
                "--force-remove-essential", "--",
                *_unnecessary_packages(bundle = _bundle, keep = (*_required_packages, *_temporary_packages))
            ))

            subprocess.check_call((
                "chroot", _bundle.as_posix(),
                "dpkg", "--purge", "--force-remove-essential", "--force-remove-protected", "--",
                *_unnecessary_packages(bundle = _bundle, keep = _required_packages)
            ))

        for _path in _unnecessary_paths:
            _path = _bundle / _path
            assert _path.is_symlink() or _path.exists(), _path.as_posix()
            _remove(path = _bundle / _path)

        with open(_bundle / "var/lib/shells.state", "w") as _stream: print("/bin/sh", file = _stream)
        for _path in _bundle.rglob("*-"): _remove(path = _path)
        for _path in _bundle.rglob("*-old"): _remove(path = _path)
        for _path in (
            *((_bundle / "etc").glob("rc*.d")),
            *((_bundle / "var/log").glob("*")),
            *((_bundle / "var/cache").glob("*"))
        ): _remove(path = _path)
        for _path in _bundle.rglob("__pycache__"):
            assert _path.resolve(strict = True) == _path
            assert _path.is_dir()
            _remove(path = _path)

        for _path in ("init", "initctl", "overlay"): (_bundle / f"sbin/{_path}").symlink_to(f"../bin/p5.lcboot.{_path}")

        _path = _current / "mount-idmapped"
        assert _path.resolve(strict = True) == _path
        assert _path.is_file()
        _path = (_bundle / "sbin").resolve(strict = True) / _path.name
        assert _path.parent.is_dir()
        assert _path.parent.is_relative_to(_bundle)
        assert not (_path.is_symlink() or _path.exists())
        shutil.copyfile(_path.name, _path)
        assert _path.resolve(strict = True) == _path
        assert _path.is_file()
        os.chown(_path, uid = 0, gid = 0)
        _path.chmod(0o755)

        _path = _destination / f"{_python_name}-{_python_version}.tar"
        assert _path.resolve(strict = False) == _path
        assert not (_path.is_symlink() or _path.exists())

        subprocess.check_call((
            "tar", "--create", "--same-owner", "--same-permissions", f"--file={_path.as_posix()}",
            f"--directory={_bundle.as_posix()}", "--", *[_p.name for _p in _bundle.glob("*")]
        ))

        assert _path.resolve(strict = True) == _path
        assert _path.is_file()
        return _path


_tar = _tar()

_ext4 = _destination / f"{_python_name}-{_python_version}.ext4"
assert _ext4.resolve(strict = False) == _ext4
assert not (_ext4.is_symlink() or _ext4.exists())
subprocess.check_call((
    "virt-make-fs", "--format=raw", "--type=ext4", "--size=+16M",
    f"--label={_python_name}", "--", _tar.as_posix(), _ext4.as_posix()
))
assert _ext4.resolve(strict = True) == _ext4
assert _ext4.is_file()

subprocess.check_call(("xz", "-9", "--", _tar.as_posix(), _ext4.as_posix()))
assert not (_tar.is_symlink() or _tar.exists())
_tar = _tar.parent / f"{_tar.name}.xz"
assert _tar.resolve(strict = True) == _tar
assert _tar.is_file()
