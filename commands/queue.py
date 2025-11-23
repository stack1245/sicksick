import discord
from utils import embed_neutral, embed_queue, embed_info


@discord.slash_command(name="대기열", description="현재 대기열 확인합니다")
async def queue(ctx: discord.ApplicationContext):
    guild_id = ctx.guild.id
    
    if guild_id not in ctx.bot.music_queues or not ctx.bot.music_queues[guild_id]:
        if guild_id in ctx.bot.now_playing:
            now = ctx.bot.now_playing[guild_id]
            embed = embed_info("", title="🎵 현재 대기열")
            embed.add_field(name="▶️ 재생 중", value=f"[{now.title}]({now.webpage_url})", inline=False)
            if now.thumbnail:
                embed.set_thumbnail(url=now.thumbnail)
        else:
            embed = embed_neutral("📦 대기열이 비어있습니다")
        await ctx.respond(embed=embed)
        return
    
    queue_list = ctx.bot.music_queues[guild_id]
    
    embed = embed_queue("", title="🎵 대기열")
    
    if guild_id in ctx.bot.now_playing:
        now = ctx.bot.now_playing[guild_id]
        embed.add_field(name="▶️ 재생 중", value=f"[{now.title}]({now.webpage_url})", inline=False)
    
    if queue_list:
        queue_text = "\n".join([f"`{i+1}.` [{song['title']}]({song['webpage_url']})" for i, song in enumerate(queue_list[:10])])
        if len(queue_list) > 10:
            queue_text += f"\n\n*+{len(queue_list) - 10}곡 더 대기 중...*"
        embed.add_field(name="🔜 대기열", value=queue_text, inline=False)
        embed.set_footer(text=f"총 {len(queue_list)}곡 대기 중")
    
    await ctx.respond(embed=embed)


def setup(bot):
    bot.add_application_command(queue)
