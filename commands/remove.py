import discord
from utils import embed_error, embed_success


@discord.slash_command(name="삭제", description="대기열에서 특정 노래를 삭제합니다")
async def remove(
    ctx: discord.ApplicationContext,
    번호: int = discord.Option(int, "삭제할 노래 번호 (1부터 시작)", min_value=1)
):
    guild_id = ctx.guild.id
    
    if guild_id not in ctx.bot.music_queues or not ctx.bot.music_queues[guild_id]:
        await ctx.respond(embed=embed_error("📦 대기열이 비어있습니다"), ephemeral=True)
        return
    
    queue = ctx.bot.music_queues[guild_id]
    
    if 번호 > len(queue):
        await ctx.respond(
            embed=embed_error(f"❌ 잘못된 번호입니다. 대기열에는 {len(queue)}곡이 있습니다"),
            ephemeral=True
        )
        return
    
    removed_song = queue.pop(번호 - 1)
    
    embed = embed_success("", title="🗑️ 삭제 완료")
    embed.add_field(name="삭제된 곡", value=f"[{removed_song['title']}]({removed_song['webpage_url']})", inline=False)
    embed.add_field(name="남은 대기열", value=f"{len(queue)}곡", inline=False)
    
    await ctx.respond(embed=embed)


def setup(bot):
    bot.add_application_command(remove)
