#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    from . import _setup_algorithms as _implementations_module
    from ... import _runtime as _runtime_module

    _make_property_collector = _runtime_module.common.property_collector.make

    _known = dict()

    def _make_decorator(key):
        assert isinstance(key, str)
        if str is not type(key): key = str(key)
        assert key

        def _result(delegate):
            assert key not in _known
            _known[key] = delegate

        return _result

    @_make_decorator(key = "lxc-libvirt")
    def _(): return _implementations_module.libvirt.lxc.run

    class _Class(object):
        def __call__(self, *args, **kwargs): return self.__implementation(*args, **kwargs)

        def __init__(self, key: str):
            super().__init__()
            assert isinstance(key, str)
            if str is not type(key): key = str(key)
            self.__implementation = _known[key]()

    return _make_property_collector(Class = _Class)


try: Class = _private().Class
finally: del _private


def make(*args, **kwargs): return Class(*args, **kwargs)
