import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


async def create_temporary_invite(guild: discord.Guild) -> str:
    try:
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).create_instant_invite:
            invite = await guild.system_channel.create_invite(
                max_age=30,
                max_uses=1,
                reason="봇 관리자 요청"
            )
            return invite.url
        
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).create_instant_invite:
                invite = await channel.create_invite(
                    max_age=30,
                    max_uses=1,
                    reason="봇 관리자 요청"
                )
                return invite.url
        
        return "❌ 초대 링크 생성 권한 없음"
    
    except discord.Forbidden:
        return "❌ 초대 링크 생성 권한 없음"
    except Exception as e:
        logger.error(f"초대 링크 생성 실패 ({guild.name}): {e}")
        return "❌ 초대 링크 생성 실패"


@discord.slash_command(name="서버목록", description="봇이 접속한 서버 목록과 초대 링크를 확인합니다 (관리자 전용)")
@commands.has_permissions(administrator=True)
async def servers(ctx: discord.ApplicationContext):
    
    await ctx.defer(ephemeral=True)
    
    guilds = ctx.bot.guilds
    total_servers = len(guilds)
    
    if total_servers == 0:
        await ctx.followup.send("접속한 서버가 없습니다.", ephemeral=True)
        return
    
    embeds = []
    current_embed = discord.Embed(
        title=f"🌐 서버 목록 ({total_servers}개)",
        description=f"봇이 현재 접속한 모든 서버의 목록입니다.",
        color=discord.Color.blue()
    )
    
    field_count = 0
    max_fields = 25
    
    for idx, guild in enumerate(sorted(guilds, key=lambda g: g.member_count, reverse=True), 1):
        if field_count >= max_fields:
            embeds.append(current_embed)
            current_embed = discord.Embed(
                title=f"🌐 서버 목록 (계속)",
                color=discord.Color.blue()
            )
            field_count = 0
        
        owner = guild.owner
        owner_info = f"{owner.mention} ({owner})" if owner else "알 수 없음"
        member_count = guild.member_count
        invite_url = await create_temporary_invite(guild)
        
        server_info = (
            f"**ID:** `{guild.id}`\n"
            f"**소유자:** {owner_info}\n"
            f"**멤버 수:** {member_count:,}명\n"
            f"**초대 링크:** {invite_url}\n"
            f"*⚠️ 1회용 30초 제한*"
        )
        
        current_embed.add_field(
            name=f"{idx}. {guild.name}",
            value=server_info,
            inline=False
        )
        field_count += 1
    
    # 마지막 embed 추가
    if field_count > 0:
        embeds.append(current_embed)
    
    # 통계 정보 추가
    total_members = sum(g.member_count for g in guilds)
    playing_count = sum(
        1 for vc in ctx.bot.voice_clients
        if isinstance(vc, discord.VoiceClient) and vc.is_playing()
    )
    
    stats_embed = discord.Embed(
        title="📊 통계",
        color=discord.Color.green()
    )
    stats_embed.add_field(name="전체 서버", value=f"{total_servers:,}개", inline=True)
    stats_embed.add_field(name="전체 멤버", value=f"{total_members:,}명", inline=True)
    stats_embed.add_field(name="재생 중", value=f"{playing_count}개 서버", inline=True)
    
    embeds.append(stats_embed)
    
    # 모든 embed를 followup으로 전송
    await ctx.followup.send(embed=embeds[0], ephemeral=True)
    
    for embed in embeds[1:]:
        await ctx.followup.send(embed=embed, ephemeral=True)


@servers.error
async def servers_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    """에러 핸들러"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.respond(
            "❌ 이 명령어는 관리자 권한이 필요합니다.",
            ephemeral=True
        )
    else:
        logger.error(f"Servers command error: {error}")
        try:
            await ctx.respond(
                f"오류가 발생했습니다: {error}",
                ephemeral=True
            )
        except:
            pass


def setup(bot):
    bot.add_application_command(servers)
