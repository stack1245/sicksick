import discord
from utils import embed_info
@discord.slash_command(name="도움말", description="봇 사용법을 확인합니다")
async def help_command(ctx: discord.ApplicationContext) -> None:
    embed = embed_info("", title=" SickSick 음악봇 도움말")
    embed.add_field(
        name=" 재생 명령어",
        value=(
            "`/재생 [노래제목/URL]` - 노래를 재생하거나 대기열에 추가\n"
            "`/일시정지` - 재생을 일시정지하거나 재개\n"
            "`/건너뛰기` - 현재 곡을 건너뜁니다\n"
            "`/중지` - 재생을 중지하고 음성 채널에서 나감"
        ),
        inline=False
    )
    embed.add_field(
        name=" 대기열 관리",
        value=(
            "`/대기열` - 현재 대기열을 확인\n"
            "`/대기열초기화` - 대기열의 모든 노래 삭제\n"
            "`/삭제 [번호]` - 대기열에서 특정 곡 삭제\n"
            "`/섞기` - 대기열 순서를 무작위로 섞기"
        ),
        inline=False
    )
    embed.add_field(
        name=" 재생 설정",
        value=(
            "`/볼륨 [0-100]` - 볼륨 조절 (없으면 현재 볼륨 표시)\n"
            "`/반복 [모드]` - 반복 모드 설정 (끄기/현재곡/대기열)\n"
            "`/현재재생` - 현재 재생 중인 노래 정보 확인"
        ),
        inline=False
    )
    embed.add_field(
        name=" 연결",
        value=(
            "`/연결` - 음성 채널에 연결\n"
            "*노래가 끝나고 대기열이 비면 자동으로 나갑니다*"
        ),
        inline=False
    )
    embed.add_field(
        name=" 특별 기능",
        value=(
            "• 싱크 가사 자동 표시 (지원되는 곡만)\n"
            "• 자동 연결/재연결\n"
            "• 노래 정보 (제목, 길이, 업로더, 조회수)\n"
            "• 볼륨 설정 저장"
        ),
        inline=False
    )
    embed.set_footer(text="SickSick Music Bot | Made with ")
    await ctx.respond(embed=embed)
def setup(bot: discord.Bot) -> None:
    """명령어 로드"""
    bot.add_application_command(help_command)
