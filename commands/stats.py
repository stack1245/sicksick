import discord
@discord.slash_command(name="통계", description="봇의 사용 통계를 확인합니다")
async def stats(ctx: discord.ApplicationContext) -> None:
    await ctx.defer()
    guilds = ctx.bot.guilds
    total_servers = len(guilds)
    total_members = sum(g.member_count for g in guilds)
    voice_clients = ctx.bot.voice_clients
    total_voice_connections = len(voice_clients)
    playing_count = sum(
        1 for vc in voice_clients
        if isinstance(vc, discord.VoiceClient) and vc.is_playing()
    )
    paused_count = sum(
        1 for vc in voice_clients
        if isinstance(vc, discord.VoiceClient) and vc.is_paused()
    )
    embed = discord.Embed(
        title=" 봇 통계",
        description="현재 봇의 사용 통계입니다.",
        color=discord.Color.blue()
    )
    embed.add_field(name="🌐 서버", value=f"```{total_servers:,}개 서버```", inline=True)
    embed.add_field(name="👥 사용자", value=f"```{total_members:,}명```", inline=True)
    embed.add_field(name=" 음성 연결", value=f"```{total_voice_connections}개```", inline=True)
    embed.add_field(name=" 재생 중", value=f"```{playing_count}개 서버```", inline=True)
    embed.add_field(name=" 일시정지", value=f"```{paused_count}개 서버```", inline=True)
    idle_count = total_voice_connections - playing_count - paused_count
    embed.add_field(name="💤 대기 중", value=f"```{idle_count}개 서버```", inline=True)
    avg_members = total_members // total_servers if total_servers > 0 else 0
    embed.add_field(name="📈 평균 멤버", value=f"```{avg_members:,}명```", inline=True)
    embed.set_footer(text=f"요청자: {ctx.author.name}",
        icon_url=ctx.author.display_avatar.url
    )
    await ctx.followup.send(embed=embed)
def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(stats)
