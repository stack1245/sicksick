import discord
from utils import embed_error, embed_info
@discord.slash_command(name="볼륨", description="볼륨을 조절합니다")
async def volume(
    ctx: discord.ApplicationContext,
    level: int = discord.Option(int, "볼륨 레벨 (0-100)", min_value=0, max_value=100, required=False)
):
    voice_client = ctx.guild.voice_client
    # 볼륨 확인만 하는 경우
    if level is None:
        if hasattr(ctx.bot, 'data_manager'):
            saved_volume = ctx.bot.data_manager.get_guild_volume(ctx.guild.id)
            emoji = "🔇" if saved_volume == 0 else "🔉" if saved_volume < 30 else "" if saved_volume < 70 else "📢"
            if voice_client and voice_client.is_playing():
                source = voice_client.source
                if hasattr(source, 'volume'):
                    current_volume = int(source.volume * 100)
                    embed = embed_info(f"{emoji} 현재 재생 볼륨: **{current_volume}%**\n저장된 기본 볼륨: **{saved_volume}%**")
                else:
                    embed = embed_info(f"{emoji} 저장된 기본 볼륨: **{saved_volume}%**")
            else:
                embed = embed_info(f"{emoji} 저장된 기본 볼륨: **{saved_volume}%**\n\n*재생 중일 때 실시간 볼륨을 조절할 수 있습니다*")
        else:
            embed = embed_error("볼륨 정보를 가져올 수 없습니다")
        await ctx.respond(embed=embed)
        return
    # 볼륨 조절
    if not voice_client or not voice_client.is_playing():
        # 재생 중이 아니어도 기본 볼륨은 설정 가능
        if hasattr(ctx.bot, 'data_manager'):
            old_volume = ctx.bot.data_manager.get_guild_volume(ctx.guild.id)
            ctx.bot.data_manager.set_guild_volume(ctx.guild.id, level)
            emoji = "🔇" if level == 0 else "🔉" if level < 30 else "" if level < 70 else "📢"
            embed = embed_info(f"{emoji} 기본 볼륨 설정: **{old_volume}%** → **{level}%**\n\n*다음 곡부터 적용됩니다*")
            await ctx.respond(embed=embed)
        else:
            await ctx.respond(embed=embed_error("재생 중인 노래가 없습니다"), ephemeral=True)
        return
    source = voice_client.source
    if not hasattr(source, 'volume'):
        await ctx.respond(embed=embed_error("현재 재생 소스는 실시간 볼륨 조절을 지원하지 않습니다."), ephemeral=True)
        return
    old_volume = int(source.volume * 100)
    source.volume = level / 100
    # 볼륨 저장
    if hasattr(ctx.bot, 'data_manager'):
        ctx.bot.data_manager.set_guild_volume(ctx.guild.id, level)
    emoji = "🔇" if level == 0 else "🔉" if level < 30 else "" if level < 70 else "📢"
    embed = embed_info(f"{emoji} 볼륨: **{old_volume}%** → **{level}%**")
    await ctx.respond(embed=embed)
def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(volume)
