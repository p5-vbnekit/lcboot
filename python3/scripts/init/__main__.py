#!/usr/bin/env python3
# -*- coding: utf-8 -*-

assert "__main__" == __name__


def _run():
    import os
    import sys

    from . import _run as _module

    _stdin = sys.stdin
    if _stdin is not None:
        _stdin = [_stdin.fileno(), _stdin]
        _stdin.pop().close()
        os.close(_stdin.pop())
    del _stdin

    _module.run()


try: _run()
finally: del _run
