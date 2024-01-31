#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    import re
    import shlex
    import typing
    import pathlib

    from ... import _runtime as _runtime_module

    _make_id_map = _runtime_module.id_map.make
    _make_property_collector = _runtime_module.common.property_collector.make

    def _make_default(): return _make_property_collector(
        root = _make_property_collector(path = pathlib.Path("/mnt/root"), mode = "pivot"),
        id_map = None, initctl = False, devices = _make_property_collector(exclude = tuple(), rexclude = tuple()),
        setup = _make_property_collector(mode = "guess", before = tuple()),
        exec = _make_property_collector(before = tuple(), command = None)
    )

    def _validate_root(value):
        if isinstance(value, str): return _validate_root(value = dict(path = value))
        assert isinstance(value, dict)
        if dict is type(value): value = value.copy()
        else: value = dict(value)
        try: _path = value.pop("path")
        except KeyError: _path = "/mnt/root"
        else:
            assert isinstance(_path, str)
            if str is not type(_path): _path = str(_path)
            assert _path
        _path = pathlib.Path(_path)
        try: _mode = value.pop("mode")
        except KeyError: _mode = "pivot"
        else:
            if _mode is not None:
                assert isinstance(_mode, str)
                if str is not type(_mode): _mode = str(_mode)
                assert _mode in {"pivot", "chroot"}
        assert not value, "unknown keys"
        return _make_property_collector(path = _path, mode = _mode)

    _number_pattern = re.compile(r"^[0-9]+$")
    _id_map_split_pattern = re.compile(r"\s+")

    def _parse_id_map_text(value):
        assert isinstance(value, str)
        if str is not type(value): value = str(value)
        value = list(_id_map_split_pattern.split(value))
        if 2 == len(value): (_internal, _external), _size = value, 1
        else:
            _internal, _external, _size = value
            assert _number_pattern.match(_size) is not None
            _size = int(_size)
            assert 0 < _size
        assert _number_pattern.match(_internal) is not None
        assert _number_pattern.match(_external) is not None
        return dict(internal = int(_internal), external = int(_external), size = _size)

    def _parse_id_map_item(value):
        if isinstance(value, str): return _parse_id_map_text(value = value)
        if isinstance(value, list):
            if 2 == len(value): (_internal, _external), _size = value, 1
            else:
                _internal, _external, _size = value
                assert 0 < _size
            assert 0 <= _internal
            assert 0 <= _external
            return dict(internal = int(_internal), external = int(_external), size = _size)
        assert isinstance(value, dict)
        if dict is type(value): value = value.copy()
        else: value = dict(value)
        _internal = value.pop("internal")
        assert isinstance(_internal, int)
        if int is not type(_internal): _internal = int(_internal)
        assert 0 <= _internal
        _external = value.pop("external")
        if int is not type(_external): _external = int(_external)
        assert 0 <= _external
        try: _size = value.pop("size")
        except KeyError: _size = 1
        else:
            assert isinstance(_size, int)
            if int is not type(_size): _size = int(_size)
            assert 0 < _size
        assert not value, "unknown keys"
        return dict(internal = int(_internal), external = int(_external), size = _size)

    def _validate_id_map_section(value):
        if isinstance(value, (str, dict)): return _make_id_map(sequence = [_parse_id_map_item(value = value)])
        assert isinstance(value, list)
        return _make_id_map(sequence = [_parse_id_map_item(value = value) for value in value])

    def _validate_id_map(value):
        if value is False: return None

        assert isinstance(value, dict)
        assert value

        if dict is type(value): value = value.copy()
        else: value = dict(value)

        try: _users = value.pop("users")
        except KeyError: _users = None
        else: _users = _validate_id_map_section(value = _users)

        try: _groups = value.pop("groups")
        except KeyError: _groups = None
        else: _groups = _validate_id_map_section(value = _groups)

        assert not value, "unknown keys"

        if _users is None: assert _groups is not None
        elif _groups is None: assert _users is not None

        return _make_property_collector(users = _users, groups = _groups)

    def _validate_initctl(value):
        assert isinstance(value, bool)
        if bool is not type(value): value = bool(value)
        return value

    def _validate_devices_exclude(value):
        if isinstance(value, str): return _validate_devices_exclude(value = [value])

        assert isinstance(value, list)

        def _validate_item(item):
            assert isinstance(item, str)
            if str is not type(item): item = str(item)
            assert item
            return item

        return tuple([_validate_item(item = _item) for _item in value])

    def _validate_devices_rexclude(value): return tuple([
        re.compile(_item) for _item in _validate_devices_exclude(value = value)
    ])

    def _validate_devices(value):
        assert isinstance(value, dict)
        if dict is type(value): value = value.copy()
        else: value = dict(value)

        try: _exclude = value.pop("exclude")
        except KeyError: _exclude = tuple()
        else: _exclude = _validate_devices_exclude(value = _exclude)

        try: _rexclude = value.pop("rexclude")
        except KeyError: _rexclude = tuple()
        else: _rexclude = _validate_devices_rexclude(value = _rexclude)

        assert not value, "unknown keys"
        return _make_property_collector(exclude = _exclude, rexclude = _rexclude)

    def _validate_command_item(value):
        assert isinstance(value, str)
        if str is not type(value): value = str(value)
        return value

    def _validate_command(value: typing.Union[str, list, dict]):
        if isinstance(value, (str, list)): return _validate_command(value = dict(command = value))

        assert isinstance(value, dict)
        if dict is type(value): value = value.copy()
        else: value = dict(value)

        _command = value.pop("command")

        if isinstance(_command, str):
            assert _command
            _command = shlex.split(_command)
        else:
            assert isinstance(_command, list)
            if list is type(_command): _command = _command.copy()
            else: _command = list(_command)

        _command = tuple([_validate_command_item(_command) for _command in _command])
        assert _command[0]

        try: _input = value.pop("input")
        except KeyError: _input = None
        else: _input = _validate_command_item(value = _input)

        assert not value, "unknown keys"
        return _make_property_collector(command = _command, input = _input)

    def _validate_commands(value):
        if value is False: return tuple()
        if isinstance(value, (str, dict)): return _validate_command(value = value),
        return tuple([_validate_command(value = value) for value in value])

    def _validate_setup_mode(value):
        if value is not None:
            assert isinstance(value, str)
            if str is not type(value): value = str(value)
            assert value
        return value

    def _validate_setup(value):
        if not isinstance(value, dict): return _validate_setup(value = dict(mode = None, before = value))
        assert isinstance(value, dict)
        if dict is type(value): value = value.copy()
        else: value = dict(value)
        try: _before = value.pop("before")
        except KeyError: _before = tuple()
        else: _before = _validate_commands(value = _before)
        try: _mode = value.pop("mode")
        except KeyError: _mode = "guess"
        else: _mode = _validate_setup_mode(value = _mode)
        assert not value, "unknown keys"
        return _make_property_collector(mode = _mode, before = _before)

    def _validate_exec(value):
        if not isinstance(value, dict): return _validate_exec(value = dict(command = value))

        if dict is type(value): value = value.copy()
        else: value = dict(value)
        assert value

        try: _before = value.pop("before")
        except KeyError: _before = tuple()
        else: _before = _validate_commands(value = _before)

        try: _command = value.pop("command")
        except KeyError: _command = None
        else:
            _command = _validate_command(value = _command)
            assert _command.input is None
            _command = _command.command

        assert not value, "unknown keys"
        return _make_property_collector(before = _before, command = _command)

    def _parse(source: typing.Optional[typing.Dict[str, typing.Any]]):
        _value = _make_default()
        if source is None: return _value

        assert isinstance(source, dict)
        if dict is type(source): source = source.copy()
        else: source = dict(source)

        try: _value.root = source.pop("root")
        except KeyError: pass
        else: _value.root = _validate_root(value = _value.root)

        try: _value.id_map = source.pop("id_map")
        except KeyError: pass
        else: _value.id_map = _validate_id_map(value = _value.id_map)

        try: _value.initctl = source.pop("initctl")
        except KeyError: pass
        else: _value.initctl = _validate_initctl(value = _value.initctl)

        try: _value.devices = source.pop("devices")
        except KeyError: pass
        else: _value.devices = _validate_devices(value = _value.devices)

        try: _value.setup = source.pop("setup")
        except KeyError: pass
        else: _value.setup = _validate_setup(value = _value.setup)

        try: _value.exec = source.pop("exec")
        except KeyError: pass
        else: _value.exec = _validate_exec(value = _value.exec)

        assert not source, "unknown keys"
        return _value

    return _make_property_collector(parse = _parse)


try: parse = _private().parse
finally: del _private
