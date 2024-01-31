#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" == __name__


def _run():
    import os
    import re
    import sys
    import typing
    import pathlib
    import argparse
    import subprocess

    import _library as _library_module

    _mounts = _library_module.mounts.make()
    _make_property_collector = _library_module.property_collector.make

    _stdin = sys.stdin
    if _stdin is not None:
        _stdin = [_stdin.fileno(), _stdin]
        _stdin.pop().close()
        os.close(_stdin.pop())
    del _stdin

    def _config():
        _arguments = argparse.ArgumentParser()
        _arguments.add_argument("destination", nargs = "?", default = "/mnt/root")
        _arguments.add_argument("--source", default = "/")
        _arguments.add_argument("--exclude", action = "append", metavar = "PATH")
        _arguments.add_argument("--rexclude", action = "append", metavar = "REGULAR_EXPRESSION")

        _arguments = list(_arguments.parse_known_args(sys.argv[1:]))
        assert not _arguments.pop(-1), "unknown arguments"
        _arguments, = _arguments
        _arguments = vars(_arguments)

        def _validate_directory(value: str):
            assert isinstance(value, str)
            if str is not type(value): value = str(value)
            assert value
            value = pathlib.Path(value).resolve()
            if value.exists(): assert value.is_dir()
            return value

        _source = _validate_directory(value = _arguments["source"])
        _destination = _validate_directory(value = _arguments["destination"])

        assert _source.exists()
        assert not _source.is_relative_to(_destination)

        def _validate_exclude(value: typing.Optional[typing.Iterable[str]]):
            if value is None: return tuple()

            def _generator():
                _unique = set()
                for _directory in value:
                    assert isinstance(_directory, str)
                    if str is not type(_directory): _directory = str(_directory)
                    assert _directory
                    _directory = pathlib.Path(_directory)
                    _parts = _directory.parts
                    if _parts and (_parts[0] not in {".", ".."}): _directory = _source / _directory
                    _directory = _directory.resolve(strict = True)
                    assert _directory != _source
                    assert _directory.is_relative_to(_source)
                    assert not _directory.is_relative_to(_destination)
                    _posix = _directory.as_posix()
                    assert _posix not in _unique
                    _unique.add(_posix)
                    yield _directory

            return tuple(_generator())

        def _validate_rexclude(value: typing.Optional[typing.Iterable[str]]):
            if value is None: return tuple()
            _list = list()
            for _pattern in value:
                assert isinstance(_pattern, str)
                if str is not type(_pattern): _pattern = str(_pattern)
                assert _pattern
                _list.append(re.compile(_pattern))
            return tuple(_list)

        return _make_property_collector(
            source = _source, destination = _destination,
            exclude = _validate_exclude(value = _arguments["exclude"]),
            rexclude = _validate_rexclude(value = _arguments["rexclude"])
        )

    _config = _config()

    def _collect(unique: bool = True):
        _filter = {_config.source.as_posix(), _config.destination.as_posix()}
        for _target in _mounts:
            if _target in _filter: continue
            _path = pathlib.Path(_target)
            assert _path.is_absolute()
            assert _path.resolve(strict = True) == _path
            if unique: _filter.add(_target)
            yield _path

    def _drop_children(source: typing.Iterable[pathlib.Path]):
        source = tuple(source)
        if not source: return

        _passed = list()

        def _condition(value: pathlib.Path):
            for _base in _passed:
                if value.is_relative_to(_base): return False
            return True

        for _path in filter(_condition, sorted(source, key = lambda v: v.as_posix())): _passed.append(_path.as_posix())
        _passed = set(_passed)
        del _condition

        def _condition(value: pathlib.Path): return value.as_posix() in _passed
        for _path in filter(_condition, source): yield _path

    def _is_expected(value: pathlib.Path):
        if not value.is_relative_to(_config.source): return False
        if value.is_relative_to(_config.destination): return False
        for _pattern in _config.exclude:
            if value.is_relative_to(_pattern): return False
        for _pattern in _config.rexclude:
            for _match in _pattern.finditer(value.relative_to(_config.source).as_posix()): return False
        return True

    def _make_unexpected():
        _value = list()
        for _destination in _collect(unique = False):
            if not _destination.is_relative_to(_config.destination): continue
            _source = _config.source / _destination.relative_to(_config.destination)
            if _is_expected(value = _source): continue
            _value.insert(0, _destination)
        return _value

    def _mount():
        for _source in _drop_children(source = filter(_is_expected, _collect(unique = True))):
            _destination = _config.destination / _source.relative_to(_config.source)
            if not _destination.exists():
                if _source.is_dir(): _destination.mkdir(parents = True, exist_ok = False)
                else:
                    _destination.parent.mkdir(parents = True, exist_ok = True)
                    _destination.touch()
            _destination.mkdir(parents = True, exist_ok = True)
            subprocess.check_call((
                "mount", "--rbind", "--", _source.as_posix(),
                (_config.destination / _source.relative_to(_config.source)).as_posix()
            ), stdin = subprocess.DEVNULL)

        for _destination in _drop_children(source = _make_unexpected()): subprocess.check_call((
            "umount", "--recursive", "--", _destination.as_posix(),
        ), stdin = subprocess.DEVNULL)

        assert not _make_unexpected()

    _mount()


_run()
