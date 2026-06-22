"""Minimal structlog-compatible logger wrapper for services/."""
from __future__ import annotations
import logging


class _KwLogger:
    __slots__ = ("_l",)

    def __init__(self, inner: logging.Logger) -> None:
        self._l = inner

    def _msg(self, msg: str, kw: dict) -> str:
        if not kw:
            return msg
        parts = " ".join(f"{k}={v!r}" for k, v in kw.items())
        return f"{msg} | {parts}"

    def debug(self, msg: str, *args, **kw) -> None:
        self._l.debug(self._msg(msg, kw), *args)

    def info(self, msg: str, *args, **kw) -> None:
        self._l.info(self._msg(msg, kw), *args)

    def warning(self, msg: str, *args, **kw) -> None:
        self._l.warning(self._msg(msg, kw), *args)

    def error(self, msg: str, *args, **kw) -> None:
        self._l.error(self._msg(msg, kw), *args)

    def exception(self, msg: str, *args, **kw) -> None:
        self._l.exception(self._msg(msg, kw), *args)


def get_logger(name: str) -> _KwLogger:
    return _KwLogger(logging.getLogger(name))
