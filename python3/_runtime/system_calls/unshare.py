#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    import ctypes
    import typing

    from .. import common as _common_module

    _make_property_collector = _common_module.property_collector.make

    _library = ctypes.CDLL(None).unshare
    _library.restype = ctypes.c_int

    _flags = _make_property_collector(
        CLONE_NEWNS = 0x00020000,
        CLONE_NEWCGROUP = 0x02000000,
        CLONE_NEWUTS = 0x04000000,
        CLONE_NEWIPC = 0x08000000,
        CLONE_NEWUSER = 0x10000000,
        CLONE_NEWNET = 0x40000000
    )

    def _validate_natural(value: int):
        assert isinstance(value, int)
        if int is not type(value): value = int(value)
        assert 0 < value
        return value

    def _make_mask(value: typing.Iterable[int]):
        _collector = 0
        for _flag in value:
            _flag = _validate_natural(value = _flag)
            assert not (_flag & _collector)
            _collector |= _flag
        return _collector

    _mask = _make_mask(value = vars(_flags).values())

    def _validate_flags(value: typing.Union[int, typing.Iterable[int]]):
        if not isinstance(value, int): value = _make_mask(value = value)
        else: value = _validate_natural(value = value)
        assert (value & _mask) == value
        return value

    class _Class(object):
        flags = _flags

        @staticmethod
        def make_mask(*flags: int): return _validate_flags(value = flags)

        def __call__(self, flags: typing.Union[int, typing.Iterable[int]]):
            assert 0 == _library(ctypes.c_int(_validate_flags(value = flags)))

    return _make_property_collector(Class = _Class)


try: Class = _private().Class
finally: del _private


def make(*args, **kwargs): return Class(*args, **kwargs)
