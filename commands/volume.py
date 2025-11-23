import discord
from utils import embed_error, embed_info


@discord.slash_command(name="볼륨", description="볼륨을 조절합니다")
async def volume(
    ctx: discord.ApplicationContext,
    level: int = discord.Option(int, "볼륨 레벨 (0-100)", min_value=0, max_value=100, required=False)
):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_playing():
        await ctx.respond(embed=embed_error("재생 중인 노래가 없습니다"), ephemeral=True)
        return
    source = voice_client.source
    if not hasattr(source, 'volume'):
        await ctx.respond(embed=embed_error("현재 재생 소스는 실시간 볼륨 조절을 지원하지 않습니다."), ephemeral=True)
        return
    current_volume = int(source.volume * 100)
    if level is None:
        emoji = "🔇" if current_volume == 0 else "🔉" if current_volume < 30 else "🔊" if current_volume < 70 else "📢"
        embed = embed_info(f"{emoji} 현재 볼륨: **{current_volume}%**")
        await ctx.respond(embed=embed)
        return
    old_volume = current_volume
    source.volume = level / 100
    emoji = "🔇" if level == 0 else "🔉" if level < 30 else "🔊" if level < 70 else "📢"
    embed = embed_info(f"{emoji} 볼륨: **{old_volume}%** → **{level}%**")
    await ctx.respond(embed=embed)


def setup(bot):
    bot.add_application_command(volume)
