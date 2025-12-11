"""상수 정의"""
from __future__ import annotations
from pathlib import Path

__all__ = [
    "DATA_DIR",
    "COLORS",
    "DEFAULT_ACTIVITY_NAME",
    "AUTO_SAVE_INTERVAL",
    "DEFAULT_SETTINGS",
    "MAX_QUEUE_SIZE",
    "DEFAULT_VOLUME",
]

# 경로
DATA_DIR = Path(__file__).parent.parent / "data"

# 색상 (0xRRGGBB 형식)
COLORS = {
    "ERROR": 0xE74C3C,
    "SUCCESS": 0x2ECC71,
    "INFO": 0x3498DB,
    "WARNING": 0xF39C12,
    "NEUTRAL": 0x95A5A6,
    "QUEUE": 0x3498DB,
    "KARAOKE": 0x9B59B6,
}

# 봇 설정
DEFAULT_ACTIVITY_NAME: str = "Sick Sick"
AUTO_SAVE_INTERVAL: int = 300

# 기본 설정
DEFAULT_SETTINGS = {
    "log_channel_id": None,
    "manager_ids": [],
}

# 음악 관련
MAX_QUEUE_SIZE: int = 50
DEFAULT_VOLUME: float = 0.3