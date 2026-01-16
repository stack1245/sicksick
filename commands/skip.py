import discord
from utils import embed_error, embed_info
@discord.slash_command(name="건너뛰기", description="현재 재생 중인 노래를 건너뜁니다")
async def skip(ctx: discord.ApplicationContext) -> None:
    voice_client = ctx.guild.voice_client
    if not voice_client:
        await ctx.respond(embed=embed_error(" 음성 채널에 연결되어 있지 않습니다"), ephemeral=True)
        return
    if not voice_client.is_connected():
        await ctx.respond(embed=embed_error(" 음성 연결이 끊어졌습니다"), ephemeral=True)
        return
    if not voice_client.is_playing():
        await ctx.respond(embed=embed_error(" 재생 중인 노래가 없습니다"), ephemeral=True)
        return
    guild_id = ctx.guild.id
    queue_count = len(ctx.bot.music_queues.get(guild_id, []))
    # 현재 재생 중인 곡 정보
    current_song = None
    if guild_id in ctx.bot.now_playing:
        current_song = ctx.bot.now_playing[guild_id]
    voice_client.stop()
    msg = "⏩ 노래를 건너뛰었습니다"
    if current_song:
        msg = f"⏩ **{current_song.title}**을(를) 건너뛰었습니다"
    if queue_count > 0:
        msg += f"\n\n🔜 다음 곡 재생 중... ({queue_count}곡 대기)"
    else:
        msg += "\n\n 대기열이 비어있습니다. 음성 채널에서 나갑니다."
    await ctx.respond(embed=embed_info(msg))
def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(skip)
