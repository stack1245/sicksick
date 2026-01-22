import discord
from utils import embed_error, embed_info, embed_success
@discord.slash_command(name="일시정지", description="재생 중인 노래를 일시정지하거나 다시 재생합니다")
async def pause(ctx: discord.ApplicationContext) -> None:
    voice_client = ctx.guild.voice_client
    if not voice_client:
        await ctx.respond(embed=embed_error(" 음성 채널에 연결되어 있지 않습니다"), ephemeral=True)
        return
    if not voice_client.is_connected():
        await ctx.respond(embed=embed_error(" 음성 연결이 끊어졌습니다"), ephemeral=True)
        return
    if not voice_client.is_playing() and not voice_client.is_paused():
        await ctx.respond(embed=embed_error(" 재생 중인 노래가 없습니다"), ephemeral=True)
        return
    if voice_client.is_playing():
        voice_client.pause()
        # 타이밍 메타데이터 업데이트
        now = asyncio.get_event_loop().time()
        ctx.bot.play_paused_at[ctx.guild.id] = now
        await ctx.respond(embed=embed_info(" 일시정지되었습니다"))
    elif voice_client.is_paused():
        now = asyncio.get_event_loop().time()
        paused_at = ctx.bot.play_paused_at.get(ctx.guild.id, now)
        offset = ctx.bot.play_offset.get(ctx.guild.id, 0.0)
        ctx.bot.play_offset[ctx.guild.id] = offset + (now - paused_at)
        ctx.bot.play_paused_at.pop(ctx.guild.id, None)
        voice_client.resume()
        await ctx.respond(embed=embed_success(" 재생이 재개되었습니다"))
def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(pause)
