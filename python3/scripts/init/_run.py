#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    import os
    import sys
    import yaml
    import pathlib
    import functools
    import traceback
    import subprocess

    from . import _cli as _cli_module
    from . import _config as _config_module
    from . import _setup_algorithm as _setup_algorithm_module
    from .. import initctl as _initctl_module
    from .. import tolerant as _tolerant_module
    from ... import _runtime as _runtime_module

    _parse_cli = _cli_module.parse
    _parse_config = _config_module.parse
    _tolerant_exec = _tolerant_module.execute
    _tolerant_spawn = _tolerant_module.spawn
    _setup_algorithm_factory = _setup_algorithm_module.make
    _make_property_collector = _runtime_module.common.property_collector.make

    _system_calls = _make_property_collector(
        exit = _runtime_module.system_calls.exit.make(),
        unshare = _runtime_module.system_calls.unshare.make(),
        pivot_root = _runtime_module.system_calls.pivot_root.make()
    )

    _system_calls.unshare = functools.partial(_system_calls.unshare, flags = _system_calls.unshare.flags.CLONE_NEWNS)

    def _validate_identification():
        def _require_root(value: int):
            assert isinstance(value, int)
            assert int is type(value)
            assert 0 == value

        _values = _make_property_collector(
            user = _make_property_collector(),
            group = _make_property_collector()
        )

        _values.user.real, _values.user.effective, _values.user.saved = os.getresuid()
        _values.group.real, _values.group.effective, _values.group.saved = os.getresgid()

        _require_root(value = _values.user.real)
        _require_root(value = _values.user.effective)
        _require_root(value = _values.user.saved)

        _require_root(value = _values.group.real)
        _require_root(value = _values.group.effective)
        _require_root(value = _values.group.saved)

    def _guess_setup_mode():
        try: _container = os.environ["container"]
        except KeyError: pass
        else:
            if "lxc-libvirt" == _container: return _container
        return None

    def _make_config():
        _cli = _parse_cli()

        def _yaml():
            _path = _cli.config
            if _path is None:
                _path = pathlib.Path("/mnt/init.yml")
                if not (_path.is_symlink() or _path.exists()): return _parse_config(source = None)
            assert isinstance(_path, pathlib.Path)
            _path = _path.resolve(strict = True)
            assert _path.is_file()
            with open(_path, "r") as _stream:
                _data = yaml.safe_load(_stream)
                assert not _stream.read(1)
            assert isinstance(_data, dict)
            return _parse_config(source = _data)

        _yaml = _yaml()

        if "guess" == _yaml.setup.mode:
            _yaml.setup.mode = _guess_setup_mode()
            assert _yaml.setup.mode is not None, "unable to guess setup mode"

        _yaml.exec.command = list() if _yaml.exec.command is None else list(_yaml.exec.command)
        if _cli.exec.override: _yaml.exec.command.clear()
        if _cli.exec.command: _yaml.exec.command.extend(_cli.exec.command)
        if not _yaml.exec.command: _yaml.exec.command.append("/sbin/init")
        _yaml.exec.command = tuple(_yaml.exec.command)

        return _yaml

    def _make_setup_algorithm(mode):
        if mode is None: return None
        return _setup_algorithm_factory(key = mode)

    def _spawn_command(command):
        if command.input is None: _tolerant_spawn(arguments = command.command, options = dict(stdin = subprocess.DEVNULL))
        else: _tolerant_spawn(arguments = command.command, options = dict(text = True, input = command.input))

    def _spawn_initctl():
        _main_pid = os.getpid()
        assert isinstance(_main_pid, int)
        assert 0 <= _main_pid

        _child_pid = os.fork()
        assert isinstance(_child_pid, int)

        if 0 == _child_pid:
            try:
                os.setsid()
                _tolerant_exec(path = sys.executable, arguments = ("-m", _initctl_module.__name__, "--", f"{_main_pid}"))
                raise RuntimeError("invalid state")

            except BaseException:
                print(traceback.format_exc(), file = sys.stderr, flush = True)
                raise

            finally: _system_calls.exit(1)

        assert 0 < _child_pid

    def _pivot(path: pathlib.Path):
        os.chdir("/")
        _tolerant_spawn(arguments = ("mount", "--make-rprivate", "--", "/"))
        _tolerant_spawn(arguments = ("mount", "--rbind", "--", path.as_posix(), path.as_posix()))
        _system_calls.pivot_root(new = path)
        os.chdir("/")
        _tolerant_spawn(arguments = ("umount", "--lazy", "--", "/"))

    def _chroot(path: pathlib.Path):
        _system_calls.pivot_root(new = path)
        os.chdir("/")

    def _run():
        _validate_identification()

        _config = _make_config()
        _setup_algorithm = _make_setup_algorithm(mode = _config.setup.mode)

        _system_calls.unshare()

        for _command in _config.setup.before: _spawn_command(command = _command)

        if not _config.root.path.is_mount(): subprocess.check_call((
            "mount", "--rbind", "--", _config.root.path.as_posix(), _config.root.path.as_posix()
        ), stdin = subprocess.DEVNULL)

        if _config.initctl: _spawn_initctl()

        if _setup_algorithm is not None: _setup_algorithm(config = _config)

        if "pivot" == _config.root.mode: _pivot(path = _config.root.path)
        elif "chroot" == _config.root.mode: _chroot(path = _config.root.path)
        else: assert _config.root.mode is None, "unknown root mode"

        for _command in _config.exec.before: _spawn_command(command = _command)
        _tolerant_exec(arguments = _config.exec.command)

    return _make_property_collector(run = _run)


try: run = _private().run
finally: del _private
