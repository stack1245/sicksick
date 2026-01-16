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
        await ctx.respond(embed=embed_info(" 일시정지되었습니다"))
    elif voice_client.is_paused():
        voice_client.resume()
        await ctx.respond(embed=embed_success(" 재생이 재개되었습니다"))
def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(pause)
