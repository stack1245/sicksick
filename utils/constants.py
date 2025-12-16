from __future__ import annotations
from pathlib import Path

__all__ = [
    "DATA_DIR",
    "COLORS",
    "DEFAULT_ACTIVITY_NAME",
    "AUTO_SAVE_INTERVAL",
    "MAX_QUEUE_SIZE",
    "DEFAULT_VOLUME",
]

DATA_DIR = Path(__file__).parent.parent / "data"

COLORS = {
    "ERROR": 0xE74C3C,
    "SUCCESS": 0x2ECC71,
    "INFO": 0x3498DB,
    "WARNING": 0xF39C12,
    "NEUTRAL": 0x95A5A6,
    "QUEUE": 0x3498DB,
}

DEFAULT_ACTIVITY_NAME: str = "Sick Sick"
AUTO_SAVE_INTERVAL: int = 300
MAX_QUEUE_SIZE: int = 50
DEFAULT_VOLUME: float = 0.05