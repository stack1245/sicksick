from __future__ import annotations
from typing import Optional
import discord

from .constants import COLORS

__all__ = [
    "make_embed",
    "embed_error",
    "embed_success",
    "embed_info",
    "embed_neutral",
    "embed_queue",
]


def _resolve_color(color: str | int) -> int:
    if isinstance(color, int):
        return color
    return COLORS.get(str(color).upper(), COLORS["INFO"])


def make_embed(
    description: Optional[str] = None,
    *,
    title: Optional[str] = None,
    color: str | int = "INFO"
) -> discord.Embed:
    return discord.Embed(
        description=description,
        title=title,
        color=_resolve_color(color)
    )


def embed_error(msg: str, title: Optional[str] = None) -> discord.Embed:
    return make_embed(msg, title=title, color="ERROR")


def embed_success(msg: str, title: Optional[str] = None) -> discord.Embed:
    return make_embed(msg, title=title, color="SUCCESS")


def embed_info(msg: str, title: Optional[str] = None) -> discord.Embed:
    return make_embed(msg, title=title, color="INFO")


def embed_neutral(msg: str, title: Optional[str] = None) -> discord.Embed:
    return make_embed(msg, title=title, color="NEUTRAL")


def embed_queue(title: str, msg: str) -> discord.Embed:
    return make_embed(msg, title=title, color="QUEUE")