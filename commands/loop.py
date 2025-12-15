import discord
from utils import embed_error, embed_info


@discord.slash_command(name="반복", description="현재 곡 또는 대기열 반복 모드를 설정합니다")
async def loop(
    ctx: discord.ApplicationContext,
    모드: str = discord.Option(
        str,
        "반복 모드",
        choices=["끄기", "현재곡", "대기열"],
        required=True
    )
):
    guild_id = ctx.guild.id
    
    if not hasattr(ctx.bot, 'loop_mode'):
        ctx.bot.loop_mode = {}
    
    mode_map = {
        "끄기": "off",
        "현재곡": "one",
        "대기열": "all"
    }
    
    mode_emoji = {
        "off": "➡️",
        "one": "🔂",
        "all": "🔁"
    }
    
    mode_text = {
        "off": "반복 모드를 껐습니다",
        "one": "현재 곡을 반복합니다",
        "all": "대기열 전체를 반복합니다"
    }
    
    selected_mode = mode_map[모드]
    ctx.bot.loop_mode[guild_id] = selected_mode
    
    emoji = mode_emoji[selected_mode]
    text = mode_text[selected_mode]
    
    await ctx.respond(embed=embed_info(f"{emoji} {text}"))


def setup(bot):
    bot.add_application_command(loop)
