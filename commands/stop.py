import discord
from utils import embed_error, embed_neutral
@discord.slash_command(name="중지", description="재생을 중지하고 음성 채널에서 나갑니다")
async def stop(ctx: discord.ApplicationContext) -> None:
    voice_client = ctx.guild.voice_client
    if not voice_client:
        await ctx.respond(embed=embed_error(" 음성 채널에 연결되어 있지 않습니다"), ephemeral=True)
        return
    # 연결이 이미 끊어진 경우 정리만 수행
    if not voice_client.is_connected():
        guild_id = ctx.guild.id
        ctx.bot.music_queues.pop(guild_id, None)
        ctx.bot.now_playing.pop(guild_id, None)
        if guild_id in ctx.bot.lyrics_tasks:
            task = ctx.bot.lyrics_tasks.pop(guild_id)
            if not task.done():
                task.cancel()
        await ctx.respond(embed=embed_neutral("⏹️ 연결이 이미 종료되었습니다"))
        return
    guild_id = ctx.guild.id
    queue_count = len(ctx.bot.music_queues.get(guild_id, []))
    # 재생 중지
    if voice_client.is_playing():
        voice_client.stop()
    # 가사 Task 정리
    if guild_id in ctx.bot.lyrics_tasks:
        task = ctx.bot.lyrics_tasks.pop(guild_id)
        if not task.done():
            task.cancel()
            try:
                await task
            except Exception:
                pass
    # 데이터 정리
    ctx.bot.music_queues.pop(guild_id, None)
    ctx.bot.now_playing.pop(guild_id, None)
    try:
        await voice_client.disconnect(force=False)
    except Exception:
        pass
    msg = "⏹️ 재생을 중지하고 연결을 해제했습니다"
    if queue_count > 0:
        msg += f"\n*({queue_count}곡이 대기열에서 삭제되었습니다)*"
    await ctx.respond(embed=embed_neutral(msg))
def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(stop)
