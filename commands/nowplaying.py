import asyncio
import time
import random
import discord

from utils import embed_neutral, embed_success, embed_info, embed_error


def _format_time(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "??:??"
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def _progress_bar(elapsed: float, duration: float | None) -> str:
    if not duration or duration <= 0:
        return "라이브 스트림"
    ratio = max(0.0, min(1.0, elapsed / duration))
    bar_len = 14
    filled = int(bar_len * ratio)
    bar = "▰" * filled + "▱" * (bar_len - filled)
    return f"{bar} { _format_time(elapsed) } / { _format_time(duration) }"


def _same_voice(interaction: discord.Interaction) -> bool:
    vc = interaction.guild.voice_client if interaction.guild else None
    if not vc or not interaction.user.voice:
        return False
    return interaction.user.voice.channel == vc.channel


class NowPlayingControls(discord.ui.View):
    def __init__(self, timeout: float = 60.0) -> None:
        super().__init__(timeout=timeout)

    async def _ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        vc = interaction.guild.voice_client if interaction.guild else None
        if not vc or not vc.is_connected():
            await interaction.response.send_message(embed=embed_error(" 음성 채널에 연결되어 있지 않습니다"), ephemeral=True)
            return None
        if not _same_voice(interaction):
            await interaction.response.send_message(embed=embed_error("같은 음성 채널에 있어야 합니다"), ephemeral=True)
            return None
        return vc

    @discord.ui.button(label="⏭️ 건너뛰기", style=discord.ButtonStyle.primary)
    async def skip_btn(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:  # type: ignore[override]
        vc = await self._ensure_voice(interaction)
        if not vc:
            return
        guild_id = interaction.guild.id
        current_song = interaction.client.now_playing.get(guild_id) if hasattr(interaction.client, "now_playing") else None
        vc.stop()
        interaction.client.play_started_at.pop(guild_id, None)
        interaction.client.play_offset.pop(guild_id, None)
        interaction.client.play_paused_at.pop(guild_id, None)
        msg = "⏩ 노래를 건너뛰었습니다"
        if current_song:
            msg = f"⏩ **{current_song.title}**을(를) 건너뛰었습니다"
        await interaction.response.send_message(embed=embed_info(msg), ephemeral=True)
        try:
            from .play import play_next  # local import to avoid cycles

            asyncio.run_coroutine_threadsafe(play_next(interaction), interaction.client.loop)
        except Exception as e:  # pragma: no cover - defensive
            import logging

            logging.getLogger(__name__).error(f"skip button play_next 실패: {e}")

    @discord.ui.button(label="⏹️ 중지", style=discord.ButtonStyle.danger)
    async def stop_btn(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:  # type: ignore[override]
        vc = await self._ensure_voice(interaction)
        if not vc:
            return
        guild_id = interaction.guild.id
        if vc.is_playing():
            vc.stop()
        interaction.client.music_queues.pop(guild_id, None)
        interaction.client.now_playing.pop(guild_id, None)
        interaction.client.play_started_at.pop(guild_id, None)
        interaction.client.play_offset.pop(guild_id, None)
        interaction.client.play_paused_at.pop(guild_id, None)
        try:
            await vc.disconnect(force=False)
        except Exception:
            pass
        await interaction.response.send_message(embed=embed_neutral("⏹️ 재생을 중지하고 나갔습니다"), ephemeral=True)

    @discord.ui.button(label="🔀 섞기", style=discord.ButtonStyle.secondary)
    async def shuffle_btn(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:  # type: ignore[override]
        vc = await self._ensure_voice(interaction)
        if not vc:
            return
        guild_id = interaction.guild.id
        queue = interaction.client.music_queues.get(guild_id, []) if hasattr(interaction.client, "music_queues") else []
        if len(queue) < 2:
            await interaction.response.send_message(embed=embed_error(" 섞을 노래가 충분하지 않습니다"), ephemeral=True)
            return
        random.shuffle(queue)
        await interaction.response.send_message(embed=embed_success(f"🔀 대기열 **{len(queue)}곡**을 섞었습니다"), ephemeral=True)


@discord.slash_command(name="현재재생", description="현재 재생 중인 노래 정보를 확인합니다")
async def nowplaying(ctx: discord.ApplicationContext) -> None:
    guild_id = ctx.guild.id
    if guild_id not in ctx.bot.now_playing:
        await ctx.respond(embed=embed_neutral(" 재생 중인 노래가 없습니다"), ephemeral=True)
        return

    now = ctx.bot.now_playing[guild_id]
    duration = getattr(now, "duration", None)

    # 경과 시간 계산
    start = ctx.bot.play_started_at.get(guild_id)
    paused_at = ctx.bot.play_paused_at.get(guild_id)
    paused_offset = ctx.bot.play_offset.get(guild_id, 0.0)
    elapsed = 0.0
    if start:
        base_now = paused_at or time.time()
        elapsed = max(0.0, (base_now - start) - paused_offset)

    embed = embed_success("", title=" 현재 재생 중")
    embed.add_field(name="제목", value=f"[{now.title}]({now.webpage_url})", inline=False)

    progress_text = _progress_bar(elapsed, duration)
    embed.add_field(name=" 진행", value=progress_text, inline=False)

    # 볼륨
    voice_client = ctx.guild.voice_client
    if voice_client and getattr(voice_client, "source", None) and hasattr(voice_client.source, "volume"):
        volume = int(voice_client.source.volume * 100)
        embed.add_field(name=" 볼륨", value=f"{volume}%", inline=True)

    # 반복 모드
    loop_mode = ctx.bot.loop_mode.get(guild_id, "off") if hasattr(ctx.bot, "loop_mode") else "off"
    loop_label = {"off": "꺼짐", "one": "현재곡", "all": "대기열"}.get(loop_mode, "꺼짐")
    embed.add_field(name=" 반복", value=loop_label, inline=True)

    # 대기열 길이
    queue_len = len(ctx.bot.music_queues.get(guild_id, [])) if hasattr(ctx.bot, "music_queues") else 0
    embed.add_field(name=" 대기열", value=f"{queue_len}곡", inline=True)

    # 업로더
    if hasattr(now, "uploader") and now.uploader:
        embed.add_field(name=" 업로더", value=now.uploader, inline=True)

    # 조회수
    if hasattr(now, "view_count") and now.view_count:
        views = now.view_count
        if views >= 1_000_000:
            view_str = f"{views/1_000_000:.1f}M"
        elif views >= 1_000:
            view_str = f"{views/1_000:.1f}K"
        else:
            view_str = str(views)
        embed.add_field(name=" 조회수", value=view_str, inline=True)

    if now.thumbnail:
        embed.set_thumbnail(url=now.thumbnail)

    requester = ctx.author.display_name
    embed.set_footer(text=f"요청자: {requester}", icon_url=ctx.author.display_avatar.url)

    await ctx.respond(embed=embed, view=NowPlayingControls())


def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(nowplaying)
