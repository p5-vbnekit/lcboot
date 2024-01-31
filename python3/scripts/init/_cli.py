#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    import sys
    import typing
    import pathlib
    import argparse

    from ... import _runtime as _runtime_module

    _make_property_collector = _runtime_module.common.property_collector.make

    def _parse():
        _arguments = argparse.ArgumentParser()
        _arguments.add_argument(
            "--config", required = False, metavar = "path", help = "config path (default: `/mnt/init.yml`)"
        )
        _arguments.add_argument("--override-exec", action = "store_true", help = "override exec command")
        _arguments.add_argument(
            "exec", nargs = "*", metavar = "command", help = "exec: override command/append arguments"
        )

        _arguments = list(_arguments.parse_known_args(sys.argv[1:]))
        assert not _arguments.pop(-1), "unknown arguments"
        _arguments, = _arguments
        _arguments = vars(_arguments)

        def _validate_config(value: typing.Optional[str]):
            if value is None: return None
            assert isinstance(value, str)
            if str is not type(value): value = str(value)
            value = pathlib.Path(value).resolve(strict = True)
            assert value.is_file()
            return value

        def _validate_exec(override: bool, command: typing.Optional[typing.Iterable[str]]):
            assert isinstance(override, bool)
            if bool is not type(override): override = bool(override)

            if command is None:
                assert override is False
                return _make_property_collector(override = override, command = None)

            def _validate_item(item: str):
                assert isinstance(item, str)
                if str is not type(item): item = str(item)
                return item

            command = [_validate_item(item = command) for command in command]
            command = tuple(command) if command else None
            if override: assert command[0]

            return _make_property_collector(override = override, command = command)

        return _make_property_collector(
            exec = _validate_exec(override = _arguments["override_exec"], command = _arguments["exec"]),
            config = _validate_config(value = _arguments["config"])
        )

    return _make_property_collector(parse = _parse)


try: parse = _private().parse
finally: del _private
