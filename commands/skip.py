import discord
from utils import embed_error, embed_info


@discord.slash_command(name="건너뛰기", description="현재 재생 중인 노래를 건너뜁니다")
async def skip(ctx: discord.ApplicationContext):
    voice_client = ctx.guild.voice_client
    
    if not voice_client or not voice_client.is_playing():
        await ctx.respond(embed=embed_error("🚫 재생 중인 노래가 없습니다"), ephemeral=True)
        return
    voice_client.stop()
    await ctx.respond(embed=embed_info("⏩ 노래를 건너뛰었습니다"))


def setup(bot):
    bot.add_application_command(skip)
