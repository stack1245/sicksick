from __future__ import annotations
import signal
import sys
from typing import Callable, List

__all__ = ["register_shutdown_callback", "setup_graceful_shutdown"]

_callbacks: List[Callable[[], None]] = []
_active = False


def register_shutdown_callback(cb: Callable[[], None]) -> None:
    _callbacks.append(cb)


def _run_callbacks() -> None:
    global _active
    if _active:
        return
    _active = True
    for cb in _callbacks:
        try:
            cb()
        except Exception:
            pass


def setup_graceful_shutdown() -> None:
    def handler(signum, frame):
        _run_callbacks()
        sys.exit(0)
    
    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            signal.signal(sig, handler)
