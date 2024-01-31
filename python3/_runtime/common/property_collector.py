#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" != __name__


def _private():
    class _Class(object):
        def __init__(self, **keywords):
            super().__init__()
            for _key, _value in keywords.items():
                assert isinstance(_key, str)
                assert _key
                assert _key == _key.strip()
                _key, = _key.splitlines()
                assert not _key.startswith("_")
            self.__dict__.update(keywords)

    return _Class


try: Class = _private()
finally: del _private


def make(*args, **kwargs): return Class(*args, **kwargs)
