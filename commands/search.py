import asyncio
import logging
import yt_dlp
import discord

from utils import embed_error, embed_info, embed_success
from .play import YTDLSource, play_next

logger = logging.getLogger(__name__)

SEARCH_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch5",
    "noplaylist": True,
    "skip_download": True,
    "source_address": "0.0.0.0",
}


def _fmt_duration(seconds: int | None) -> str:
    if seconds is None:
        return "라이브"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


class SearchSelectView(discord.ui.View):
    def __init__(self, results, author_id: int, *, timeout: float = 90.0) -> None:
        super().__init__(timeout=timeout)
        self.results = results
        self.author_id = author_id
        for idx, item in enumerate(results[:5], 1):
            label = f"{idx}. {item['title'][:60]}"
            self.add_item(SearchButton(label=label, idx=idx - 1))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:  # type: ignore[override]
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(embed=embed_error("검색을 실행한 사용자만 선택할 수 있습니다"), ephemeral=True)
            return False
        return True


class SearchButton(discord.ui.Button):
    def __init__(self, *, label: str, idx: int) -> None:
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.idx = idx

    async def callback(self, interaction: discord.Interaction) -> None:  # type: ignore[override]
        view: SearchSelectView = self.view  # type: ignore
        selection = view.results[self.idx]
        user = interaction.user
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(embed=embed_error("길드 정보가 없습니다"), ephemeral=True)
            return
        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(embed=embed_error("먼저 음성 채널에 참가해주세요"), ephemeral=True)
            return

        channel = user.voice.channel
        voice_client = guild.voice_client

        # 연결/이동
        if not voice_client or not voice_client.is_connected():
            try:
                voice_client = await channel.connect(timeout=15.0, reconnect=True)
                await asyncio.sleep(0.3)
            except Exception as e:
                await interaction.response.send_message(embed=embed_error(f"음성 연결 실패: {str(e)}"), ephemeral=True)
                return
        elif voice_client.channel != channel:
            try:
                await voice_client.move_to(channel)
            except Exception as e:
                await interaction.response.send_message(embed=embed_error(f"채널 이동 실패: {str(e)}"), ephemeral=True)
                return

        guild_id = guild.id
        if guild_id not in interaction.client.music_queues:
            interaction.client.music_queues[guild_id] = []

        queue = interaction.client.music_queues[guild_id]
        is_playing = voice_client.is_connected() and voice_client.is_playing()

        # append or play
        if is_playing:
            queue.append(selection)
            embed = embed_success("", title=" 재생목록에 추가")
            embed.add_field(name="제목", value=f"[{selection['title']}]({selection['webpage_url']})", inline=False)
            if selection.get("duration"):
                embed.add_field(name=" 재생시간", value=_fmt_duration(selection["duration"]), inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            try:
                volume = interaction.client.data_manager.get_guild_volume(guild_id) / 100 if hasattr(interaction.client, "data_manager") else 0.05
                player = await YTDLSource.prepare_player(selection, loop=interaction.client.loop, volume=volume)
            except Exception as e:
                await interaction.response.send_message(embed=embed_error(f"재생 준비 실패: {str(e)}"), ephemeral=True)
                return

            def after_play(err):
                if err:
                    logger.error(f"검색 선택 재생 오류: {err}")
                try:
                    asyncio.run_coroutine_threadsafe(play_next(interaction), interaction.client.loop)
                except Exception as e:  # pragma: no cover
                    logger.error(f"검색 선택 다음 곡 예약 실패: {e}")

            try:
                voice_client.play(player, after=after_play)
                interaction.client.now_playing[guild_id] = player
                now = asyncio.get_event_loop().time()
                interaction.client.play_started_at[guild_id] = now
                interaction.client.play_offset[guild_id] = 0.0
                interaction.client.play_paused_at.pop(guild_id, None)
            except Exception as e:
                await interaction.response.send_message(embed=embed_error(f"재생 실패: {str(e)}"), ephemeral=True)
                return

            embed = embed_success("", title=" 재생 중")
            embed.add_field(name="제목", value=f"[{selection['title']}]({selection['webpage_url']})", inline=False)
            if selection.get("duration"):
                embed.add_field(name=" 재생시간", value=_fmt_duration(selection["duration"]), inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)


@discord.slash_command(name="검색", description="노래를 검색하고 선택하여 재생/추가합니다")
async def search(
    ctx: discord.ApplicationContext,
    제목_또는_url: str = discord.Option(str, description="검색할 노래 제목 또는 URL"),
):
    if not ctx.author.voice:
        await ctx.respond(embed=embed_error("먼저 음성 채널에 참가해주세요"), ephemeral=True)
        return

    await ctx.defer()
    query = 제목_또는_url
    try:
        with yt_dlp.YoutubeDL(SEARCH_OPTIONS) as ydl:
            data = ydl.extract_info(query, download=False)
            entries = data.get("entries", []) if data else []
            results = []
            for item in entries[:5]:
                if not item:
                    continue
                results.append(
                    {
                        "webpage_url": item.get("webpage_url") or item.get("url"),
                        "title": item.get("title"),
                        "duration": item.get("duration"),
                        "thumbnail": item.get("thumbnail"),
                        "uploader": item.get("uploader"),
                        "view_count": item.get("view_count"),
                    }
                )
            if not results:
                await ctx.followup.send(embed=embed_error("검색 결과가 없습니다"), ephemeral=True)
                return

            desc_lines = []
            for idx, item in enumerate(results, 1):
                dur = _fmt_duration(item.get("duration"))
                desc_lines.append(f"`{idx}.` [{item['title']}]({item['webpage_url']}) • {dur}")
            embed = embed_info("\n".join(desc_lines), title=" 검색 결과 (최대 5개)")
            view = SearchSelectView(results, ctx.author.id)
            await ctx.followup.send(embed=embed, view=view)
    except Exception as e:
        logger.error(f"검색 실패: {e}")
        await ctx.followup.send(embed=embed_error(f"검색 중 오류 발생: {str(e)}"), ephemeral=True)


def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(search)
