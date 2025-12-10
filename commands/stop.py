import discord
from utils import embed_error, embed_neutral


@discord.slash_command(name="중지", description="재생을 중지하고 음성 채널에서 나갑니다")
async def stop(ctx: discord.ApplicationContext):
    voice_client = ctx.guild.voice_client
    
    if not voice_client:
        await ctx.respond(embed=embed_error("🚫 음성 채널에 연결되어 있지 않습니다"), ephemeral=True)
        return
    
    guild_id = ctx.guild.id
    queue_count = len(ctx.bot.music_queues.get(guild_id, []))
    
    # 재생 중지
    if voice_client.is_playing():
        voice_client.stop()
    
    # 데이터 정리
    ctx.bot.music_queues.pop(guild_id, None)
    ctx.bot.now_playing.pop(guild_id, None)
    
    # 안전하게 연결 해제
    try:
        await voice_client.disconnect(force=False)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"연결 해제 중 오류 (무시됨): {e}")
    
    msg = "⏹️ 재생을 중지하고 연결을 해제했습니다"
    if queue_count > 0:
        msg += f"\n*({queue_count}곡이 대기열에서 삭제되었습니다)*"
    await ctx.respond(embed=embed_neutral(msg))


def setup(bot):
    bot.add_application_command(stop)
