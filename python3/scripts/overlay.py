#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def _private():
    import os
    import sys
    import shutil
    import typing
    import pathlib
    import argparse
    import contextlib
    import subprocess

    from .. import _runtime as _runtime_module

    _make_property_collector = _runtime_module.common.property_collector.make

    def _make_config():
        _arguments = argparse.ArgumentParser()
        _arguments.add_argument("layers", nargs = "*")
        _arguments.add_argument("--path", type = str, default = "/mnt/root", metavar = "DIRECTORY_PATH")
        _arguments.add_argument("--cache", default = "/mnt/cache/overlay", metavar = "DIRECTORY_PATH")

        _arguments = list(_arguments.parse_known_args(sys.argv[1:]))
        assert not _arguments.pop(-1), "unknown arguments"
        _arguments, = _arguments
        _arguments = vars(_arguments)

        def _validate_directory(value: str, strict: bool = False):
            assert isinstance(value, str)
            if str is not type(value): value = str(value)
            assert value
            value = pathlib.Path(value).resolve(strict = False)
            if strict or value.exists(): assert value.is_dir()
            return value

        _path = _validate_directory(value = _arguments["path"], strict = True)
        _cache = _validate_directory(value = _arguments["cache"])

        def _check_cache_conflicts(path: pathlib.Path):
            if _cache.is_relative_to(path): return False
            if not path.is_relative_to(_cache): return True
            if path.is_relative_to(_cache / "temp"): return False
            if path.is_relative_to(_cache / "upper"): return False
            return True

        assert _check_cache_conflicts(path = _path)

        def _validate_layers(value: typing.Iterable[str]):
            _list = list()
            for value in value:
                value = _validate_directory(value = value, strict = True)
                for _base in _list: assert not value.is_relative_to(_base)
                else: assert not value.is_relative_to(_path)
                assert _check_cache_conflicts(path = _path)
                _list.append(value)
            return tuple(_list)

        return _make_property_collector(
            path = _path, cache = _cache,
            layers = _validate_layers(value = _arguments["layers"])
        )

    @contextlib.contextmanager
    def _manager():
        _config = _make_config()

        def _ids():
            _value = _config.path.stat()
            _value = _make_property_collector(user = _value.st_uid, group = _value.st_gid)
            assert isinstance(_value.user, int)
            assert isinstance(_value.group, int)
            assert 0 <= _value.user
            assert 0 <= _value.group
            _value = _make_property_collector(source = _value, effective = _make_property_collector(
                user = os.geteuid(), group = os.getegid()
            ))
            assert isinstance(_value.effective.user, int)
            assert isinstance(_value.effective.group, int)
            assert 0 <= _value.effective.user
            assert 0 <= _value.effective.group
            return _value

        _ids = _ids()

        def _update_permissions(path: pathlib.Path, mode: int = 0o700, effective: bool = True):
            assert isinstance(path, pathlib.Path)
            path = pathlib.Path(path.as_posix()).resolve(strict = True)
            assert isinstance(mode, int)
            if int is not type(mode): mode = int(mode)
            assert isinstance(effective, bool)
            _id_source = _ids.effective if effective else _ids.source
            os.chown(path, uid = _id_source.user, gid = _id_source.group)
            path.chmod(mode = mode)

        _cache = _config.cache
        _cache.mkdir(parents = True, exist_ok = True)
        _update_permissions(path = _cache)
        _cache = _make_property_collector(
            temp = _cache / "temp", upper = _cache / "upper"
        )
        assert not _cache.temp.is_mount()
        assert not _cache.upper.is_mount()
        if _cache.temp.exists(): shutil.rmtree(_cache.temp)
        _cache.temp.mkdir(parents = False, exist_ok = False)
        _cache.upper.mkdir(parents = False, exist_ok = True)
        _update_permissions(path = _cache.temp)
        _update_permissions(path = _cache.upper, mode = 0o755, effective = False)

        _cache.temp = _make_property_collector(
            path = _cache.temp, layers = list(), links = 0
        )

        (_cache.temp.path / "w").mkdir(parents = False, exist_ok = False)
        _update_permissions(path = _cache.temp.path / "w")

        def _make_link(path: pathlib.Path):
            _name = "{:x}".format(_cache.temp.links)
            (_cache.temp.path / _name).symlink_to(path)
            _cache.temp.links += 1
            return _name

        def _remove_link(name: str):
            _path = _cache.temp.path / name
            assert _cache.temp.path == _path.parent
            assert _path.is_symlink()
            _path.unlink()

        def _finally():
            _remove_link(name = "u")
            for _name in _cache.temp.layers: _remove_link(name = _name)

        try:
            (_cache.temp.path / "u").symlink_to(f"../{_cache.upper.name}")
            _cache.temp.layers.append(_make_link(path = _config.path))
            _cache.temp.layers.extend([_make_link(path = _path) for _path in _config.layers])
            yield _make_property_collector(
                path = _cache.temp.path, work = "w",
                layers = tuple(_cache.temp.layers), upper = "u"
            )

        finally: _finally()

    def _run():
        with _manager() as _context:
            _command = ":".join(reversed(_context.layers))
            _command = ",".join((f"workdir={_context.work}", f"lowerdir={_command}", f"upperdir={_context.upper}"))
            _command = ("mount", "--types=overlay", f"--options={_command}", "--", "overlay", f"./{_context.layers[0]}")
            subprocess.check_call(_command, stdin = subprocess.DEVNULL, cwd = _context.path)

    return _make_property_collector(run = _run)


try: run = _private().run
finally: del _private

if "__main__" == __name__: run()
