import discord
from utils import embed_error, embed_success


@discord.slash_command(name="연결", description="음성 채널에 연결합니다")
async def join(ctx: discord.ApplicationContext):
    if not ctx.author.voice:
        await ctx.respond(
            embed=embed_error("🚫 먼저 음성 채널에 참가해주세요"),
            ephemeral=True
        )
        return
    
    channel = ctx.author.voice.channel
    voice_client = ctx.guild.voice_client
    
    if voice_client:
        if voice_client.channel == channel:
            await ctx.respond(
                embed=embed_error("❌ 이미 이 음성 채널에 연결되어 있습니다"),
                ephemeral=True
            )
            return
        else:
            try:
                await voice_client.move_to(channel)
                await ctx.respond(embed=embed_success(f"🔊 **{channel.name}**(으)로 이동했습니다"))
            except Exception as e:
                await ctx.respond(embed=embed_error(f"❌ 채널 이동 실패: {str(e)}"), ephemeral=True)
    else:
        try:
            await channel.connect(timeout=15.0, reconnect=True)
            await ctx.respond(embed=embed_success(f"🔊 **{channel.name}**에 연결했습니다"))
        except Exception as e:
            await ctx.respond(embed=embed_error(f"❌ 연결 실패: {str(e)}"), ephemeral=True)


def setup(bot):
    bot.add_application_command(join)
