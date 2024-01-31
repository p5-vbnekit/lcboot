#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def _private():
    import os
    import re
    import sys
    import shutil
    import typing
    import pathlib
    import subprocess

    from .. import _runtime as _runtime_module

    _make_property_collector = _runtime_module.common.property_collector.make

    def _which(value):
        assert value not in {"/", ".", ".."}
        _value = shutil.which(value)
        if not (isinstance(_value, str) and _value): raise FileNotFoundError(value)
        return pathlib.Path(_value).resolve(strict = True)

    def _validate_path(value):
        _which_condition = False

        if isinstance(value, str):
            if str is not type(value): value = str(value)
            assert value
            assert "\0" not in value
            _which_condition = "/" not in value
            value = pathlib.Path(value)
            if _which_condition: _which_condition = value.parts and value.parts[0] not in {".", ".."}

        else:
            assert isinstance(value, pathlib.Path)
            value = pathlib.Path(value.as_posix())

        value = _make_property_collector(original = value)
        if _which_condition:
            value.resolved = _which(value = value.original.as_posix())
            assert value.resolved.is_file()
        else: value.resolved = value.original.resolve(strict = True)
        value.original = value.original.as_posix()

        return value

    def _validate_arguments(value):
        def _generate():
            for _value in value:
                assert isinstance(_value, str)
                if str is not type(_value): _value = str(value)
                yield _value

        return tuple(_generate())

    def _parse_shebang(path):
        with open(path, "rb") as _command:
            assert b"#!" == _command.read(2)
            _command = _command.readline()

        _command = _command.strip().decode("utf-8")
        assert _command
        _command = re.compile(r"\s").split(_command)
        _command = _command.pop(0), _command
        assert _command[0]
        return _command

    def _resolve(path, arguments, walk):
        if arguments is None: arguments = list()
        else: arguments = list(arguments)
        if path is None: path = _validate_path(value = arguments.pop(0))
        else: path = _validate_path(value = path)

        _recursion_protector = set()

        def _generate(command):
            if command.path.resolved.is_dir():
                _posix = command.path.resolved.as_posix()
                if not walk: raise IsADirectoryError(_posix)
                assert _posix not in _recursion_protector
                _recursion_protector.add(_posix)
                try:
                    for _path in sorted(command.path.resolved.glob("*"), key = lambda p: p.name): yield from _generate(
                        command = _make_property_collector(path = _validate_path(value = _path), arguments = command.arguments)
                    )
                finally: _recursion_protector.remove(_posix)
                return

            assert command.path.resolved.is_file()
            if os.access(command.path.resolved, os.X_OK):
                yield command
                return

            _executable, _arguments = _parse_shebang(path = command.path.resolved)
            _executable = _validate_path(value = _executable)
            _arguments.append(command.path.original)
            _arguments.extend(command.arguments)
            yield _make_property_collector(path = _executable, arguments = _arguments)

        return tuple(_generate(command = _make_property_collector(path = path, arguments = arguments)))

    def _run():
        _command = _resolve(path = None, arguments = _validate_arguments(value = sys.argv[1:]), walk = True)
        assert _command
        if 1 == len(_command):
            _command, = _command
            assert _command.path.resolved.is_file()
            _command.arguments.insert(0, _command.path.original)
            os.execv(_command.path.resolved, _command.arguments)
            raise RuntimeError("unexpected state")
        for _command in _command: subprocess.check_call((_command.path.resolved.as_posix(), *_command.arguments))

    def _spawn(
        path: typing.Union[str, pathlib.Path] = None,
        arguments: typing.Iterable[str] = None,
        options: typing.Dict[str, typing.Any] = None
    ):
        if options is None: options = dict()
        else: assert isinstance(options, dict) and options
        for _command in _resolve(
            path = path, arguments = _validate_arguments(value = arguments), walk = True
        ): assert 0 == subprocess.run((_command.path.resolved.as_posix(), *_command.arguments), **options).returncode

    def _execute(path: typing.Union[str, pathlib.Path] = None, arguments: typing.Iterable[str] = None):
        _command, = _resolve(path = path, arguments = _validate_arguments(value = arguments), walk = False)
        assert _command.path.resolved.is_file()
        _command.arguments.insert(0, _command.path.original)
        os.execv(_command.path.resolved, _command.arguments)
        raise RuntimeError("unexpected state")

    return _make_property_collector(run = _run, spawn = _spawn, execute = _execute)


_private = _private()

try:
    run = _private.run
    spawn = _private.spawn
    execute = _private.execute
finally: del _private

if "__main__" == __name__: run()
