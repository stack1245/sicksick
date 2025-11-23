"""봇 종료 시 안전하게 리소스 정리"""
from __future__ import annotations
import signal
import sys
from typing import Callable, List

__all__ = ["register_shutdown_callback", "setup_graceful_shutdown"]

_callbacks: List[Callable[[], None]] = []
_active = False

def register_shutdown_callback(cb: Callable[[], None]) -> None:
    """종료 시 실행할 콜백 등록"""
    _callbacks.append(cb)

def _run_callbacks() -> None:
    """등록된 모든 종료 콜백 실행"""
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
    """시그널 핸들러 설정"""
    def handler(signum, frame):
        _run_callbacks()
        sys.exit(0)
    
    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            signal.signal(sig, handler)
