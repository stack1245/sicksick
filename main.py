"""Sicksick - 음악 및 가라오케 봇"""
from __future__ import annotations
import asyncio
import os
import sys

import discord
from dotenv import load_dotenv

from utils.extension_loader import ExtensionLoader
from utils.data_manager import DataManager
from utils.constants import AUTO_SAVE_INTERVAL, DEFAULT_ACTIVITY_NAME
from utils.graceful_shutdown import setup_graceful_shutdown, register_shutdown_callback
from utils.logging_config import configure_logging

load_dotenv()
configure_logging()

import logging
logger = logging.getLogger(__name__)


class MusicBot(discord.Bot):
    """음악 봇 - 재생 및 가라오케"""

    def __init__(self) -> None:
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
        self.lyrics_tasks = {}
        self.loop_mode = {}
        self._initialized = False
        self._auto_save_task: asyncio.Task | None = None
        self._status_update_task: asyncio.Task | None = None

    async def on_ready(self) -> None:
        """봇 준비 완료"""
        if self._initialized or not self.user:
            return
        
        try:
            await self._initialize()
            self._initialized = True
            print(f"[{self.user.name}] 준비 완료")
        except Exception as e:
            logger.error(f"초기화 실패: {e}", exc_info=e)
            await self.close()

    async def _initialize(self) -> None:
        """초기화 로직"""
        self.data_manager.load_data()
        
        self.extension_loader.load_extension_groups("commands")
        if self.extension_loader.failed_extensions:
            for ext_name, error in self.extension_loader.failed_extensions:
                logger.error(f"명령어 로드 실패: {ext_name}\n{error}")
        
        if self._auto_save_task is None or self._auto_save_task.done():
            self._auto_save_task = asyncio.create_task(self._auto_save_loop())
        
        if self._status_update_task is None or self._status_update_task.done():
            self._status_update_task = asyncio.create_task(self._status_update_loop())
        
        await self._update_status()

    async def _auto_save_loop(self) -> None:
        """주기적 데이터 저장"""
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await asyncio.sleep(AUTO_SAVE_INTERVAL)
                self.data_manager.save_data()
                logger.debug("자동 저장 완료")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"자동 저장 오류: {e}")

    async def _status_update_loop(self) -> None:
        """주기적 상태 업데이트"""
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await asyncio.sleep(30)
                await self._update_status()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"상태 업데이트 오류: {e}")

    async def _update_status(self) -> None:
        """재생 중인 음악 수 기반 상태 설정"""
        try:
            playing_count = sum(
                1 for vc in self.voice_clients
                if isinstance(vc, discord.VoiceClient) and vc.is_playing()
            )
            
            if playing_count > 0:
                status_text = f"{playing_count}개 서버에서 재생 중"
                activity_type = discord.ActivityType.playing
            else:
                total_guilds = len(self.guilds)
                status_text = f"{total_guilds}개 서버 | /재생 명령어"
                activity_type = discord.ActivityType.listening
            
            await self.change_presence(
                activity=discord.Activity(
                    type=activity_type,
                    name=status_text
                )
            )
        except Exception as e:
            logger.error(f"상태 업데이트 오류: {e}")

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        """음성 채널 상태 변경 감지"""
        if member.id != self.user.id:
            return
        
        if before.channel and not after.channel:
            guild_id = before.channel.guild.id
            
            if guild_id in self.lyrics_tasks:
                task = self.lyrics_tasks.pop(guild_id)
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self.music_queues.pop(guild_id, None)
            self.now_playing.pop(guild_id, None)
            self.karaoke_sessions.pop(guild_id, None)
            self.loop_mode.pop(guild_id, None)
            
            try:
                await self._update_status()
            except Exception as e:
                logger.error(f"상태 업데이트 오류: {e}")

    async def on_application_command_error(
        self,
        context: discord.ApplicationContext,
        error: discord.DiscordException
    ) -> None:
        """명령어 오류 처리"""
        logger.error(f"명령어 오류: {error}", exc_info=error)
        
        if isinstance(error, discord.ClientException):
            error_str = str(error).lower()
            if "not connected" in error_str or "already playing" in error_str:
                if context.guild and context.guild.voice_client:
                    try:
                        vc = context.guild.voice_client
                        if vc.is_playing():
                            vc.stop()
                        await vc.disconnect(force=True)
                        logger.debug(f"Voice client 정리: {context.guild.id}")
                    except Exception as e:
                        logger.error(f"Voice client 정리 오류: {e}")
        
        try:
            embed = discord.Embed(
                description=f"오류 발생: {str(error)[:100]}",
                color=0xE74C3C
            )
            if not context.response.is_done():
                await context.respond(embed=embed, ephemeral=True)
            else:
                await context.followup.send(embed=embed, ephemeral=True)
        except Exception:
            pass

    async def close(self) -> None:
        """봇 종료 처리"""
        if self._auto_save_task and not self._auto_save_task.done():
            self._auto_save_task.cancel()
            try:
                await self._auto_save_task
            except asyncio.CancelledError:
                pass
        
        if self._status_update_task and not self._status_update_task.done():
            self._status_update_task.cancel()
            try:
                await self._status_update_task
            except asyncio.CancelledError:
                pass
        
        for guild_id, task in list(self.lyrics_tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.lyrics_tasks.clear()
        
        if self.data_manager:
            self.data_manager.save_data()
            logger.debug("종료 전 데이터 저장")
        
        for vc in list(self.voice_clients):
            try:
                if vc.is_playing():
                    vc.stop()
                await vc.disconnect(force=True)
            except Exception:
                pass
        
        await super().close()


def main() -> None:
    """봇 실행"""
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN 미설정")
        return

    bot = MusicBot()

    def shutdown_handler():
        asyncio.create_task(bot.close())

    register_shutdown_callback(shutdown_handler)
    setup_graceful_shutdown()

    try:
        bot.run(token)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
