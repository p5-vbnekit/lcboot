#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    import io
    import typing

    from . import common as _common_module

    _make_property_collector = _common_module.property_collector.make

    def _make_item(internal: int, external: int, size: int = 1):
        assert isinstance(internal, int)
        assert isinstance(external, int)
        assert isinstance(size, int)
        if int is not type(internal): internal = int(internal)
        if int is not type(external): external = int(external)
        if int is not type(size): size = int(size)
        assert 0 <= internal
        assert 0 <= external
        assert 0 < size
        return _make_property_collector(internal = internal, external = external, size = size)

    def _find(value, mapping, reverse):
        assert isinstance(value, int)
        if int is not type(value): value = int(value)
        assert 0 <= value

        if reverse: _key = lambda: mapping.external
        else: _key = lambda: mapping.internal

        for mapping in mapping:
            _min = _key()
            if value < _min: continue
            _max = _min + mapping.size - 1
            if value > _max: continue
            return mapping

        return None

    def _validate_sequence(sequence):
        sequence = [_make_item(**_item) for _item in sequence]

        _internal = sorted(sequence, key = lambda item: item.internal)
        _iterator = iter(_internal)
        _item = next(_iterator)
        _previous = _item
        for _item in _iterator:
            assert _previous.internal + _previous.size <= _item.internal, "internal interception"
            _previous = _item

        _iterator = iter(sorted(sequence, key = lambda item: item.external))
        _item = next(_iterator)
        _previous = _item
        for _item in _iterator:
            assert _previous.external + _previous.size <= _item.external, "external interception"
            _previous = _item

        return tuple(_internal)

    def _make_text(sequence):
        with io.StringIO() as _stream:
            for _item in sequence: print(f"{_item.internal} {_item.external} {_item.size}", file = _stream)
            return _stream.getvalue()

    class _Class(object):
        @property
        def text(self): return self.__text

        def __call__(self, value: int):
            _item = _find(value = value, mapping = self.__sequence, reverse = False)
            if _item is None: return None
            return (value - _item.internal) + _item.external

        def __init__(self, sequence: typing.Iterable[typing.Dict[str, int]]):
            super().__init__()
            sequence = _validate_sequence(sequence = sequence)
            self.__text = _make_text(sequence = sequence)
            self.__sequence = sequence

    return _make_property_collector(Class = _Class)


try: Class = _private().Class
finally: del _private


def make(*args, **kwargs): return Class(*args, **kwargs)
