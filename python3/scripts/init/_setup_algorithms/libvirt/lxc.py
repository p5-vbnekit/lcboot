#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    import os
    import re
    import sys
    import typing
    import signal
    import pathlib
    import functools
    import subprocess

    from ..... import _runtime as _runtime_module

    _make_property_collector = _runtime_module.common.property_collector.make

    _PropertyCollector = _runtime_module.common.PropertyCollector

    _system_calls = _make_property_collector(
        exit = _runtime_module.system_calls.exit.make(),
        unshare = _runtime_module.system_calls.unshare.make()
    )

    def _parse_environment():
        _type = os.environ["container"]
        assert isinstance(_type, str) and (str is type(_type))
        assert "lxc-libvirt" == os.environ["container"]
        _name = os.environ["LIBVIRT_LXC_NAME"]
        assert isinstance(_name, str) and (str is type(_name))
        assert _name.strip() == _name
        _name, = _name.splitlines()
        _uuid = os.environ["LIBVIRT_LXC_UUID"]
        assert isinstance(_uuid, str) and (str is type(_uuid))
        assert re.match(r"^[0-9a-f][\-0-9a-f]{34}[0-9a-f]$", _uuid, re.IGNORECASE) is not None
        return _name

    def _resolve_next(path):
        assert isinstance(path, pathlib.Path)
        assert path.is_absolute()
        assert path.is_symlink()
        _path = pathlib.Path(os.readlink(path))
        if not _path.is_absolute(): _path = path.parent / _path
        return _path

    def _generate_network_interfaces():
        _path = pathlib.Path("/sys/class/net").resolve(strict = True)
        assert _path.is_dir()
        for _path in _path.glob("*"):
            if "lo" == _path.name: continue
            yield _path.name

    def _mount_devices(root: pathlib.Path):
        _base_path = root / "dev"
        subprocess.check_call(("mount", "--types=tmpfs", "--", "devfs", _base_path.as_posix()), stdin = subprocess.DEVNULL)

        _path = _base_path / "pts"
        _path.mkdir(parents = False, exist_ok = False)
        subprocess.check_call(("mount", "--types=devpts", "--", "devpts", _path.as_posix()), stdin = subprocess.DEVNULL)

        _path = _base_path / "shm"
        _path.mkdir(parents = False, exist_ok = False)
        subprocess.check_call(("mount", "--types=tmpfs", "--", "shm", _path.as_posix()), stdin = subprocess.DEVNULL)

        _path = _base_path / "mqueue"
        _path.mkdir(parents = False, exist_ok = False)
        subprocess.check_call(("mount", "--types=mqueue", "--", "mqueue", _path.as_posix()), stdin = subprocess.DEVNULL)

        pathlib.Path(_base_path / "ptmx").symlink_to("pts/ptmx")

        def _iteration(source: pathlib.Path):
            _destination = root / source.relative_to("/")
            if _destination.is_symlink(): return
            if _destination.exists(): return
            if _source.is_symlink():
                _destination.symlink_to(os.readlink(_source))
                return
            if _source.is_dir():
                _destination.mkdir(parents = False, exist_ok = False)
                if _source.is_mount():
                    subprocess.check_call((
                        "mount", "--rbind", "--", _source.as_posix(), _destination.as_posix()
                    ), stdin = subprocess.DEVNULL)
                    return
                for source in source.glob("*"): _iteration(source = source)
                return
            _destination.touch()
            subprocess.check_call((
                "mount", "--bind", "--", _source.as_posix(), _destination.as_posix()
            ), stdin = subprocess.DEVNULL)

        for _source in pathlib.Path("/dev").glob("*"): _iteration(source = _source)

    def _make_id_map(source: typing.Optional[_PropertyCollector]):
        _result = _make_property_collector(
            users = _make_property_collector(text = None, root = None),
            groups = _make_property_collector(text = None, root = None)
        )

        if source is not None:
            if source.users is not None:
                _result.users.text = source.users.text.strip()
                _result.users.root = source.users(value = 0)
                if _result.users.root is None:
                    _result.users.text = f"0 0 1\n{_result.users.text}"
                    _result.users.root = 0

            if source.groups is not None:
                _result.groups.text = source.groups.text.strip()
                _result.groups.root = source.groups(value = 0)
                if _result.groups.root is None:
                    _result.groups.text = f"0 0 1\n{_result.groups.text}"
                    _result.groups.root = 0

        return _result

    def _make_owner_changer(id_map: _PropertyCollector):
        _kwargs = dict()
        _id = id_map.users.root
        if (_id is not None) and (0 < _id): _kwargs.update(uid = _id)
        _id = id_map.groups.root
        if (_id is not None) and (0 < _id): _kwargs.update(gid = _id)
        if not _kwargs: return None

        def _result(path: str | pathlib.PurePath):
            if isinstance(path, pathlib.PurePath): path = pathlib.Path(path.as_posix())
            else: path = pathlib.Path(path)
            assert path.exists()

            _unique = set()

            def _routine(cursor: pathlib.Path):
                os.lchown(cursor, **_kwargs)
                if cursor.is_symlink():
                    _routine(cursor = _resolve_next(cursor))
                    return
                cursor = cursor.resolve(strict = False)
                if not cursor.exists(): return
                if not cursor.is_dir(): return
                _posix = cursor.as_posix()
                if _posix in _unique: return
                _unique.add(_posix)
                for cursor in cursor.glob("*"): _routine(cursor = cursor)

            _routine(cursor = path)

        return _result

    def _prepare_cgroup(change_owner: typing.Optional[typing.Callable]):
        with open("/proc/self/cgroup", mode = "r", encoding = "utf-8") as _content:
            _content, = _content.read().splitlines(keepends = False)
        _content = list(_content.split(":"))
        assert "0" == _content.pop(0)
        assert not _content.pop(0)
        assert _content
        _content = ":".join(_content)
        assert "/" == _content[0]
        _content = _content[1:]
        assert _content[0] not in {"/", ".", ".."}
        assert pathlib.Path(_content).as_posix() == _content
        _path = pathlib.Path("/sys/fs/cgroup")
        assert _path.resolve(strict = True) == _path
        assert _path.is_dir() and _path.is_mount()
        _path = _path / _content
        assert _path.resolve(strict = True) == _path
        assert _path.is_dir()
        _content = tuple(_path.glob("*"))
        assert _content
        _content = tuple(_content for _content in _content if _content.is_dir())
        assert not _content
        _pid = os.getpid()
        assert isinstance(_pid, int)
        assert 0 < _pid
        with open(_path / "cgroup.procs", mode = "r", encoding = "ascii") as _content: _content, = (
            _content for _content in _content.read().splitlines(keepends = False) if "0" != _content
        )
        assert _content == str(_pid)
        if change_owner is None: return
        change_owner(path = _path)

    def _prepare_devices(change_owner: typing.Callable):
        for _device in (
            "null", "full", "zero",
            "random", "urandom",
            "console", "tty", "tty1"
        ): change_owner(path = f"/dev/{_device}")

    def _unshare(id_map: _PropertyCollector, network_interfaces: typing.Iterable[str]):
        network_interfaces = tuple(network_interfaces)

        _system_call = _system_calls.unshare

        _flags = [
            _system_call.flags.CLONE_NEWCGROUP,
            _system_call.flags.CLONE_NEWUTS,
            _system_call.flags.CLONE_NEWIPC,
            _system_call.flags.CLONE_NEWNET
        ]

        if id_map.users.text or id_map.groups.text: _flags.extend((
            _system_call.flags.CLONE_NEWNS, _system_call.flags.CLONE_NEWUSER
        ))

        _system_call = functools.partial(_system_call, flags = _flags)
        del _flags

        if not (id_map.users.text or id_map.groups.text or network_interfaces):
            _system_call()
            return

        _target_pid = os.getpid()
        assert isinstance(_target_pid, int)
        assert 0 < _target_pid
        _target_pid = pathlib.Path(f"/proc/{_target_pid}")
        assert _target_pid.resolve(strict = True) == _target_pid
        assert _target_pid.is_dir()

        _magic = 42
        _descriptor = os.eventfd(0, 0)
        assert isinstance(_descriptor, int)
        assert 0 <= _descriptor

        _target_uid = id_map.users.root
        _target_gid = id_map.groups.root
        if _target_uid is None: _target_uid = 0
        if _target_gid is None: _target_gid = 0

        try:
            _status = 1
            _pid = os.fork()
            assert isinstance(_pid, int)
            if 0 == _pid:
                try:
                    assert _magic == os.eventfd_read(_descriptor)
                    if id_map.users.text:
                        with open(_target_pid / "uid_map", "w") as _stream: print(id_map.users.text, file = _stream)
                    if id_map.groups.text:
                        with open(_target_pid / "gid_map", "w") as _stream: print(id_map.groups.text, file = _stream)
                    for _interface in network_interfaces: subprocess.check_call((
                        "ip", "link", "set", _interface, "netns", (_target_pid / "ns/net").as_posix()
                    ), stdin = subprocess.DEVNULL)
                except BaseException:
                    import traceback
                    print(traceback.format_exc(), file = sys.stderr, flush = True)
                    raise
                else: _status = 0
                finally: _system_calls.exit(_status)

            assert 0 < _pid
            _system_call()
            os.eventfd_write(_descriptor, _magic)
            _target_pid, _status = os.waitpid(_pid, 0)
            assert isinstance(_target_pid, int)
            assert _target_pid == _pid
            _status = os.waitstatus_to_exitcode(_status)
            assert isinstance(_status, int)
            assert 0 == _status

        finally: os.close(_descriptor)

    def _run(config: _PropertyCollector):
        _root = config.root.path
        assert isinstance(_root, pathlib.Path)
        _root = _root.resolve(strict = True)
        assert _root.is_dir()
        assert 1 < len(_root.parts)

        _id_map = _make_id_map(source = config.id_map)

        if config.devices.exclude: raise NotImplementedError("config.devices.exclude")
        if config.devices.rexclude: raise NotImplementedError("config.devices.rexclude")

        # clear any inherited settings, see `unshare.c` from util-linux source code
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

        _change_owner = _make_owner_changer(id_map = _id_map)
        _prepare_cgroup(change_owner = _change_owner)
        _network_interfaces = tuple(_generate_network_interfaces())
        if _change_owner is not None: _prepare_devices(change_owner = _change_owner)

        subprocess.check_call(("mount", "--types=proc", "--", "proc", (_root / "proc").as_posix()), stdin = subprocess.DEVNULL)

        _unshare(id_map = _id_map, network_interfaces = _network_interfaces)

        os.setgid(0)
        os.setuid(0)

        _mount_devices(root = _root)

        subprocess.check_call((
            "mount", "--types=sysfs", "--options=ro,nodev,nosuid,noexec",
            "--", "sysfs", (_root / "sys").as_posix()
        ), stdin = subprocess.DEVNULL)

        subprocess.check_call((
            "mount", "--types=cgroup2", "--options=rw,nodev,nosuid,noexec",
            "--", "cgroup2", (_root / "sys/fs/cgroup").as_posix()
        ), stdin = subprocess.DEVNULL)

    return _make_property_collector(run = _run)


try: run = _private().run
finally: del _private
