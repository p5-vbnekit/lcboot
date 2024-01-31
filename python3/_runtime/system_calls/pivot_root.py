#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    import ctypes
    import typing
    import pathlib

    from .. import common as _common_module

    _make_property_collector = _common_module.property_collector.make

    _library = ctypes.CDLL(None).pivot_root
    _library.restype = ctypes.c_int

    def _validate_path(value: typing.Union[str, pathlib.Path]):
        if isinstance(value, pathlib.Path): value = value.as_posix()
        else: assert isinstance(value, str)
        value = pathlib.Path(value).resolve(strict = True)
        assert value.is_dir()
        assert 1 < len(value.parts)
        return value

    class _Class(object):
        def __call__(self, new: typing.Union[str, pathlib.Path], old: typing.Union[str, pathlib.Path] = None):
            new = _validate_path(value = new)
            if old is None: old = new
            else:
                old = _validate_path(value = old)
                assert old.is_relative_to(new)
            _current = pathlib.Path(".").resolve(strict = True)
            assert _current.is_dir()
            new = ctypes.c_char_p(new.as_posix().encode("utf-8"))
            old = ctypes.c_char_p(old.as_posix().encode("utf-8"))
            assert 0 == _library(new, old)

    return _make_property_collector(Class = _Class)


try: Class = _private().Class
finally: del _private


def make(*args, **kwargs): return Class(*args, **kwargs)
