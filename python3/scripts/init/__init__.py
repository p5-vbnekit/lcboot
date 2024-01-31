#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    from ... import _runtime as _runtime_module

    _make_lazy = _runtime_module.common.lazy_attributes.make_getter
    _make_property_collector = _runtime_module.common.property_collector.make

    return _make_property_collector(lazy = _make_lazy(dictionary = dict(
        run = lambda module: getattr(module, "_run").run
    )))


_private = _private()

__all__ = _private.lazy.keys
__date__ = None
__author__ = None
__version__ = None
__credits__ = None
_fields = tuple()
__bases__ = tuple()


def __getattr__(name: str): return _private.lazy(name = name)
