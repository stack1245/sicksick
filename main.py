"""SickSick Music Bot - Discord music player bot."""
from __future__ import annotations
import os
import asyncio
import logging
from typing import Optional
import discord
from dotenv import load_dotenv

from utils.extension_loader import ExtensionLoader
from utils.data_manager import DataManager
from utils.logging import configure_logging
from utils.graceful_shutdown import setup_graceful_shutdown, register_shutdown_callback
from utils.constants import DEFAULT_ACTIVITY_NAME, AUTO_SAVE_INTERVAL

load_dotenv()
configure_logging()
logger = logging.getLogger("sicksick")


class MusicBot(discord.Bot):
    """Discord music bot with playlist and karaoke support."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        
        super().__init__(intents=intents)
        
        self.data_manager = DataManager(self)
        self.extension_loader = ExtensionLoader(self)
        self.music_queues = {}
        self.now_playing = {}
        self.karaoke_sessions = {}
        self._commands_loaded = False
        self._auto_save_task: Optional[asyncio.Task] = None
    
    async def on_ready(self) -> None:
        if not self.user:
            return
        
        if not self._commands_loaded:
            try:
                self.data_manager.load_data()
                self.extension_loader.load_all_extensions()
                await self.sync_commands()
                self._commands_loaded = True
                print(f"[{self.user.name}] 준비 완료")
            except Exception as e:
                logger.error(f"초기화 실패: {e}")
                return
        
        try:
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name=DEFAULT_ACTIVITY_NAME
                )
            )
        except Exception as e:
            logger.error(f"상태 변경 실패: {e}")
        
        if not self._auto_save_task:
            self._auto_save_task = self.loop.create_task(self._auto_save_loop())
    
    async def _auto_save_loop(self) -> None:
        """Periodically save bot data."""
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(AUTO_SAVE_INTERVAL)
            try:
                self.data_manager.save_data()
            except Exception as e:
                logger.error(f"자동 저장 실패: {e}")
    
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Handle voice state changes, especially bot disconnections."""
        if member.id != self.user.id:
            return
        
        # 봇이 음성 채널에서 강제 퇴장당했을 때
        if before.channel and not after.channel:
            guild_id = before.channel.guild.id
            # logger.info(f"Guild {guild_id}: 음성 채널에서 연결 해제됨")
            
            # 대기열 및 재생 정보 정리
            self.music_queues.pop(guild_id, None)
            self.now_playing.pop(guild_id, None)
            self.karaoke_sessions.pop(guild_id, None)
    
    async def on_application_command_error(
        self,
        ctx: discord.ApplicationContext,
        error: discord.DiscordException,
    ) -> None:
        logger.error(f"명령어 오류: {ctx.command.name if ctx.command else '알 수 없음'} - {error}")
        
        try:
            if not ctx.response.is_done():
                await ctx.respond(f"오류가 발생했습니다: {error}", ephemeral=True)
        except Exception:
            pass
    
    async def close(self) -> None:
        """Cleanup resources and close bot connection."""
        try:
            if self._auto_save_task:
                self._auto_save_task.cancel()
            self.data_manager.save_data()
            
            for vc in self.voice_clients:
                await vc.disconnect()
        except Exception as e:
            logger.error(f"종료 처리 실패: {e}")
        finally:
            await super().close()


def main():
    """Main entry point for the bot."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN이 설정되지 않음")
        return
    
    bot = MusicBot()
    register_shutdown_callback(lambda: bot.data_manager.save_data())
    setup_graceful_shutdown()
    
    try:
        bot.run(token)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"봇 실행 오류: {e}")


if __name__ == "__main__":
    main()