"""통계 명령어"""
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


@discord.slash_command(
    name="통계",
    description="봇의 사용 통계를 확인합니다"
)
async def stats(ctx: discord.ApplicationContext):
    """봇의 전체 통계 정보 표시"""
    
    await ctx.defer()
    
    guilds = ctx.bot.guilds
    total_servers = len(guilds)
    
    # 통계 수집
    total_members = sum(g.member_count for g in guilds)
    
    # 음성 채널 통계
    voice_clients = ctx.bot.voice_clients
    total_voice_connections = len(voice_clients)
    
    # 재생 중인 서버 수
    playing_count = sum(
        1 for vc in voice_clients
        if isinstance(vc, discord.VoiceClient) and vc.is_playing()
    )
    
    # 일시정지된 서버 수
    paused_count = sum(
        1 for vc in voice_clients
        if isinstance(vc, discord.VoiceClient) and vc.is_paused()
    )
    
    # Embed 생성
    embed = discord.Embed(
        title="📊 봇 통계",
        description="현재 봇의 사용 통계입니다.",
        color=discord.Color.blue()
    )
    
    # 서버 정보
    embed.add_field(
        name="🌐 서버",
        value=f"```{total_servers:,}개 서버```",
        inline=True
    )
    
    # 사용자 정보
    embed.add_field(
        name="👥 사용자",
        value=f"```{total_members:,}명```",
        inline=True
    )
    
    # 음성 연결
    embed.add_field(
        name="🔊 음성 연결",
        value=f"```{total_voice_connections}개```",
        inline=True
    )
    
    # 재생 중
    embed.add_field(
        name="▶️ 재생 중",
        value=f"```{playing_count}개 서버```",
        inline=True
    )
    
    # 일시정지
    embed.add_field(
        name="⏸️ 일시정지",
        value=f"```{paused_count}개 서버```",
        inline=True
    )
    
    # 대기 중
    idle_count = total_voice_connections - playing_count - paused_count
    embed.add_field(
        name="💤 대기 중",
        value=f"```{idle_count}개 서버```",
        inline=True
    )
    
    # 평균 정보
    avg_members = total_members // total_servers if total_servers > 0 else 0
    embed.add_field(
        name="📈 서버당 평균 멤버",
        value=f"```{avg_members:,}명```",
        inline=True
    )
    
    # 봇 정보
    embed.set_footer(
        text=f"요청자: {ctx.author.name}",
        icon_url=ctx.author.display_avatar.url
    )
    
    await ctx.followup.send(embed=embed)
    logger.info(f"통계 명령어 실행 - {ctx.author} (서버: {ctx.guild.name})")


@stats.error
async def stats_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    """에러 핸들러"""
    logger.error(f"Stats command error: {error}")
    try:
        await ctx.respond(
            f"통계를 불러오는 중 오류가 발생했습니다: {error}",
            ephemeral=True
        )
    except:
        pass


def setup(bot):
    bot.add_application_command(stats)
