from __future__ import annotations
import logging

__all__ = ["configure_logging"]

_SUPPRESS_LOGGERS = (
    "discord",
    "discord.client",
    "discord.gateway",
    "discord.http",
)


def configure_logging(level: int = logging.ERROR) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level, format="%(message)s")
    
    for logger_name in _SUPPRESS_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
