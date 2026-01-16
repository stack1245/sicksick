import discord
from utils import embed_neutral, embed_success
@discord.slash_command(name="현재재생", description="현재 재생 중인 노래 정보를 확인합니다")
async def nowplaying(ctx: discord.ApplicationContext) -> None:
    guild_id = ctx.guild.id
    if guild_id not in ctx.bot.now_playing:
        await ctx.respond(embed=embed_neutral(" 재생 중인 노래가 없습니다"), ephemeral=True)
        return
    now = ctx.bot.now_playing[guild_id]
    embed = embed_success("", title=" 현재 재생 중")
    embed.add_field(name="제목", value=f"[{now.title}]({now.webpage_url})", inline=False)
    # 재생시간
    if now.duration:
        minutes = now.duration // 60
        seconds = now.duration % 60
        embed.add_field(
            name=" 재생시간",
            value=f"{minutes}:{seconds:02d}",
            inline=True
        )
    # 볼륨
    voice_client = ctx.guild.voice_client
    if voice_client:
        volume = int(voice_client.source.volume * 100)
        embed.add_field(name=" 볼륨", value=f"{volume}%", inline=True)
    # 업로더
    if hasattr(now, 'uploader') and now.uploader:
        embed.add_field(name=" 업로더", value=now.uploader, inline=True)
    # 조회수
    if hasattr(now, 'view_count') and now.view_count:
        views = now.view_count
        if views >= 1000000:
            view_str = f"{views/1000000:.1f}M"
        elif views >= 1000:
            view_str = f"{views/1000:.1f}K"
        else:
            view_str = str(views)
        embed.add_field(name=" 조회수", value=view_str, inline=True)
    if now.thumbnail:
        embed.set_thumbnail(url=now.thumbnail)
    await ctx.respond(embed=embed)
def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(nowplaying)
