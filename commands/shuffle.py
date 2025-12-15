import discord
import random
from utils import embed_error, embed_success


@discord.slash_command(name="섞기", description="대기열의 노래 순서를 무작위로 섞습니다")
async def shuffle(ctx: discord.ApplicationContext):
    guild_id = ctx.guild.id
    
    if guild_id not in ctx.bot.music_queues or not ctx.bot.music_queues[guild_id]:
        await ctx.respond(embed=embed_error("📦 대기열이 비어있습니다"), ephemeral=True)
        return
    
    queue = ctx.bot.music_queues[guild_id]
    
    if len(queue) < 2:
        await ctx.respond(embed=embed_error("🎲 섞을 노래가 충분하지 않습니다 (최소 2곡 필요)"), ephemeral=True)
        return
    
    random.shuffle(queue)
    
    await ctx.respond(embed=embed_success(f"🔀 대기열 **{len(queue)}곡**의 순서를 무작위로 섞었습니다"))


def setup(bot):
    bot.add_application_command(shuffle)
