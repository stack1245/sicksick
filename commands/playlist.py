import asyncio
import discord

from utils import embed_error, embed_success, embed_info
from .play import YTDLSource, play_next


@discord.slash_command(name="대기열저장", description="현재 대기열을 이름으로 저장합니다")
async def save_queue(
    ctx: discord.ApplicationContext,
    이름: str = discord.Option(str, description="저장할 이름"),
) -> None:
    guild_id = ctx.guild.id
    queue = ctx.bot.music_queues.get(guild_id, []) if hasattr(ctx.bot, "music_queues") else []
    if not queue:
        await ctx.respond(embed=embed_error(" 저장할 대기열이 없습니다"), ephemeral=True)
        return
    ctx.bot.save_playlist_named(guild_id, 이름, queue)
    await ctx.respond(embed=embed_success(f"'{이름}' 이름으로 대기열 {len(queue)}곡을 저장했습니다"))


@discord.slash_command(name="대기열불러오기", description="저장된 대기열을 불러와 재생합니다")
async def load_queue(
    ctx: discord.ApplicationContext,
    이름: str = discord.Option(str, description="불러올 이름"),
) -> None:
    if not ctx.author.voice:
        await ctx.respond(embed=embed_error("먼저 음성 채널에 참가해주세요"), ephemeral=True)
        return

    guild_id = ctx.guild.id
    playlist = ctx.bot.load_playlist_named(guild_id, 이름)
    if not playlist:
        await ctx.respond(embed=embed_error(f"'{이름}' 플레이리스트를 찾을 수 없습니다"), ephemeral=True)
        return

    # 연결 준비
    channel = ctx.author.voice.channel
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        try:
            voice_client = await channel.connect(timeout=15.0, reconnect=True)
            await asyncio.sleep(0.3)
        except Exception as e:
            await ctx.respond(embed=embed_error(f"음성 연결 실패: {str(e)}"), ephemeral=True)
            return
    elif voice_client.channel != channel:
        try:
            await voice_client.move_to(channel)
        except Exception as e:
            await ctx.respond(embed=embed_error(f"채널 이동 실패: {str(e)}"), ephemeral=True)
            return

    # 대기열 교체
    ctx.bot.music_queues[guild_id] = list(playlist)

    if voice_client.is_playing():
        await ctx.respond(embed=embed_success(f"'{이름}'을(를) 불러왔습니다. 현재 곡 이후 {len(playlist)}곡 대기"))
        return

    # 즉시 재생 시작
    try:
        first = ctx.bot.music_queues[guild_id].pop(0)
        volume = ctx.bot.data_manager.get_guild_volume(guild_id) / 100 if hasattr(ctx.bot, "data_manager") else 0.05
        player = await YTDLSource.prepare_player(first, loop=ctx.bot.loop, volume=volume)
    except Exception as e:
        await ctx.respond(embed=embed_error(f"재생 준비 실패: {str(e)}"), ephemeral=True)
        return

    def after_play(err):
        if err:
            import logging

            logging.getLogger(__name__).error(f"대기열불러오기 재생 오류: {err}")
        try:
            asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop)
        except Exception:
            pass

    voice_client.play(player, after=after_play)
    ctx.bot.now_playing[guild_id] = player
    now = asyncio.get_event_loop().time()
    ctx.bot.play_started_at[guild_id] = now
    ctx.bot.play_offset[guild_id] = 0.0
    ctx.bot.play_paused_at.pop(guild_id, None)

    embed = embed_success("", title=" 재생 중")
    embed.add_field(name="제목", value=f"[{first['title']}]({first['webpage_url']})", inline=False)
    await ctx.respond(embed=embed)


@discord.slash_command(name="대기열목록", description="저장된 대기열 목록을 확인합니다")
async def list_queues(ctx: discord.ApplicationContext) -> None:
    names = ctx.bot.list_playlists(ctx.guild.id)
    if not names:
        await ctx.respond(embed=embed_info("저장된 대기열이 없습니다"), ephemeral=True)
        return
    formatted = "\n".join([f"• {name}" for name in names])
    embed = embed_info(formatted, title=" 저장된 대기열")
    await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(save_queue)
    bot.add_application_command(load_queue)
    bot.add_application_command(list_queues)
