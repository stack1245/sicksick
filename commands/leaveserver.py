"""서버 나가기 명령어"""
import discord
from discord import Option
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


@discord.slash_command(
    name="leaveserver",
    description="봇이 지정한 서버에서 나갑니다 (관리자 전용)"
)
@commands.has_permissions(administrator=True)
async def leaveserver(
    ctx: discord.ApplicationContext,
    server_id: str = Option(description="나갈 서버의 ID")
):
    """봇이 지정한 서버에서 나가기"""
    
    await ctx.defer(ephemeral=True)
    
    try:
        # 서버 ID를 정수로 변환
        guild_id = int(server_id)
    except ValueError:
        await ctx.followup.send("❌ 잘못된 서버 ID입니다. 숫자로 입력해주세요.", ephemeral=True)
        return
    
    # 서버 찾기
    guild = ctx.bot.get_guild(guild_id)
    
    if not guild:
        await ctx.followup.send(
            f"❌ ID가 `{guild_id}`인 서버를 찾을 수 없습니다.\n"
            "봇이 해당 서버에 접속해있지 않거나 잘못된 ID입니다.",
            ephemeral=True
        )
        return
    
    # 현재 서버에서 나가려는 경우 경고
    if guild.id == ctx.guild.id:
        await ctx.followup.send(
            "⚠️ 현재 이 명령어를 실행하는 서버에서 나가려고 합니다.\n"
            "정말 나가시겠습니까? 다시 초대받기 전까지 이 서버의 명령어를 사용할 수 없습니다.",
            ephemeral=True
        )
    
    # 서버 정보 저장
    server_name = guild.name
    server_member_count = guild.member_count
    
    # 확인 메시지
    embed = discord.Embed(
        title="🚪 서버 나가기 확인",
        description=f"다음 서버에서 나가시겠습니까?",
        color=discord.Color.orange()
    )
    embed.add_field(name="서버 이름", value=server_name, inline=True)
    embed.add_field(name="서버 ID", value=f"`{guild_id}`", inline=True)
    embed.add_field(name="멤버 수", value=f"{server_member_count:,}명", inline=True)
    
    # 버튼 추가
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.value = None
        
        @discord.ui.button(label="나가기", style=discord.ButtonStyle.danger, emoji="🚪")
        async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.value = True
            self.stop()
            
            # 서버 나가기 실행
            try:
                await guild.leave()
                
                success_embed = discord.Embed(
                    title="✅ 서버에서 나갔습니다",
                    description=f"**{server_name}** 서버에서 성공적으로 나갔습니다.",
                    color=discord.Color.green()
                )
                success_embed.add_field(name="서버 ID", value=f"`{guild_id}`", inline=True)
                success_embed.add_field(name="멤버 수", value=f"{server_member_count:,}명", inline=True)
                
                await interaction.response.edit_message(embed=success_embed, view=None)
                logger.info(f"봇이 서버에서 나감: {server_name} (ID: {guild_id})")
                
            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ 오류 발생",
                    description=f"서버에서 나가는 중 오류가 발생했습니다: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=error_embed, view=None)
                logger.error(f"서버 나가기 실패: {server_name} (ID: {guild_id}) - {e}")
        
        @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, emoji="❌")
        async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.value = False
            self.stop()
            
            cancel_embed = discord.Embed(
                title="취소됨",
                description="서버 나가기를 취소했습니다.",
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=cancel_embed, view=None)
    
    view = ConfirmView()
    await ctx.followup.send(embed=embed, view=view, ephemeral=True)
    
    # 타임아웃 처리
    await view.wait()
    if view.value is None:
        timeout_embed = discord.Embed(
            title="⏱️ 시간 초과",
            description="60초 동안 응답이 없어 취소되었습니다.",
            color=discord.Color.greyple()
        )
        try:
            await ctx.edit(embed=timeout_embed, view=None)
        except:
            pass


@leaveserver.error
async def leaveserver_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    """에러 핸들러"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.respond(
            "❌ 이 명령어는 관리자 권한이 필요합니다.",
            ephemeral=True
        )
    else:
        logger.error(f"Leaveserver command error: {error}")
        try:
            await ctx.respond(
                f"오류가 발생했습니다: {error}",
                ephemeral=True
            )
        except:
            pass


def setup(bot):
    bot.add_application_command(leaveserver)
