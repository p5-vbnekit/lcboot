#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    import os
    import sys
    import ctypes
    import traceback
    import contextlib

    from .. import common as _common_module

    _make_property_collector = _common_module.property_collector.make

    _libc = ctypes.CDLL(None).exit
    _libc.restype = None

    try: _os = getattr(os, "_exit")
    except AttributeError: _os = None

    try: _sys = sys.exit
    except AttributeError: _sys = None

    def _validate_code(value: int):
        assert isinstance(value, int)
        if int is not type(value): value = int(value)
        return value

    @contextlib.contextmanager
    def _exception_manager():
        try: yield
        except BaseException:
            print(traceback.print_exc(), file = sys.stderr, flush = True)
            raise
        finally: return

    def _invoke(code: int):
        code = _validate_code(value = code)
        with _exception_manager(): _libc(ctypes.c_int(code))
        if _os is not None:
            with _exception_manager: _os(code)
        if _sys is not None:
            with _exception_manager: _sys(code)
        exit(code)

    class _Class(object):
        def __call__(self, code: int = 0): _invoke(code = code)

    return _make_property_collector(Class = _Class)


try: Class = _private().Class
finally: del _private


def make(*args, **kwargs): return Class(*args, **kwargs)
