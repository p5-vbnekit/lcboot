#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def _private():
    import os
    import sys
    import signal
    import ctypes
    import typing
    import argparse

    from .. import _runtime as _runtime_module

    _make_property_collector = _runtime_module.common.property_collector.make

    def _run():
        def _config():
            _arguments = argparse.ArgumentParser()
            _arguments.add_argument("pid", nargs = "?", metavar = "PID")

            _arguments = list(_arguments.parse_known_args(sys.argv[1:]))
            assert not _arguments.pop(-1), "unknown arguments"
            _arguments, = _arguments
            _arguments = vars(_arguments)

            def _validate_pid(value: typing.Optional[str]):
                if value is None: return None
                assert isinstance(value, str)
                if str is not type(value): value = str(value)
                if not value: return 0
                _value = int(value)
                assert str(_value) == value
                assert 0 < _value
                return _value

            return _make_property_collector(pid = _validate_pid(value = _arguments["pid"]))

        _config = _config()

        def _pid():
            _my = os.getpid()
            assert isinstance(_my, int)
            assert 0 < _my

            _parent = os.getppid()
            assert isinstance(_parent, int)
            if 0 == _parent: assert 1 == _my
            else: assert 0 < _parent

            if 0 == _config.pid: return None
            if _config.pid is not None:
                assert 1 < _my
                return _config.pid

            if 0 < _parent: return _parent
            return None

        _pid = _pid()

        """
        // from systemd-initctl: https://github.com/systemd/systemd/tree/main/src/initctl
        #define INIT_CMD_RUNLVL 1

        struct init_request {
        int	magic;      /* Magic number */
        int	cmd;        /* What kind of request */
        int	runlevel;   /* Runlevel to change to */
        int	sleeptime;  /* Time between TERM and KILL */
        union {
            struct init_request_bsd	bsd;
            char data[368];
        } i;
        };
        """
        class _RequestHead(ctypes.Structure): pass
        _RequestHead._fields_ = (
            ("magic", ctypes.c_int),
            ("command", ctypes.c_int),
            ("level", ctypes.c_int)
        )

        _request_size = ctypes.sizeof(_RequestHead) + 369
        _request_magic = 0x03091969
        _request_command = 1  # INIT_CMD_RUNLVL
        _request_levels = {ord(_level) for _level in ("0", "6")}

        _path = "/dev/initctl"

        assert os.mkfifo(_path) is None

        try:
            with open("/dev/initctl", mode = "rb") as _stream:
                while True:
                    _request = _stream.read(_request_size)
                    assert isinstance(_request, bytes)
                    assert _request_size == len(_request)
                    _request = _RequestHead.from_buffer_copy(_request)
                    assert _request_magic == _request.magic
                    if _request_command != _request.command: continue
                    if _request.level in _request_levels: break

        finally: os.remove(_path)

        if _pid is not None: assert os.kill(_pid, signal.SIGTERM) is None

    return _make_property_collector(run = _run)


try: run = _private().run
finally: del _private

if "__main__" == __name__: run()
