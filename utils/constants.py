"""씩씩이 음악 봇 상수"""
from __future__ import annotations

__all__ = [
    "COLORS",
    "DEFAULT_ACTIVITY_NAME",
    "AUTO_SAVE_INTERVAL",
]

COLORS = {
    "ERROR": 0xE74C3C,
    "SUCCESS": 0x2ECC71,
    "INFO": 0x3498DB,
    "NEUTRAL": 0x95A5A6,
    "QUEUE": 0x3498DB,
    "KARAOKE": 0x9B59B6,
}

DEFAULT_ACTIVITY_NAME: str = "Sick Sick"
AUTO_SAVE_INTERVAL: int = 300