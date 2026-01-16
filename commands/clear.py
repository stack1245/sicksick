import discord
from utils import embed_error, embed_success
@discord.slash_command(name="대기열초기화", description="대기열의 모든 노래를 삭제합니다")
async def clear(ctx: discord.ApplicationContext) -> None:
    guild_id = ctx.guild.id
    if guild_id not in ctx.bot.music_queues or not ctx.bot.music_queues[guild_id]:
        await ctx.respond(embed=embed_error(" 대기열이 비어있습니다"), ephemeral=True)
        return
    count = len(ctx.bot.music_queues[guild_id])
    ctx.bot.music_queues[guild_id].clear()
    await ctx.respond(embed=embed_success(f" 대기열에서 **{count}곡**을 삭제했습니다"))
def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(clear)
