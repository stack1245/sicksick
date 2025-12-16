"""SickSick 음악 봇"""
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
    """음악 재생 및 대기열 관리 봇"""
    
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
        self.lyrics_tasks = {}  # 가사 표시 Task 추적
        self.loop_mode = {}  # 반복 모드 (off, one, all)
        self._commands_loaded = False
        self._auto_save_task: Optional[asyncio.Task] = None
        self._status_update_task: Optional[asyncio.Task] = None
        self._closing = False
    
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
        
        # 초기 상태 설정
        await self._update_status()
        
        if not self._auto_save_task:
            self._auto_save_task = self.loop.create_task(self._auto_save_loop())
        
        if not self._status_update_task:
            self._status_update_task = self.loop.create_task(self._status_update_loop())
    
    async def _auto_save_loop(self) -> None:
        """주기적 데이터 저장"""
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(AUTO_SAVE_INTERVAL)
            try:
                self.data_manager.save_data()
            except Exception as e:
                logger.error(f"자동 저장 실패: {e}")
    
    async def _status_update_loop(self) -> None:
        """주기적 상태 업데이트"""
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(30)  # 30초마다 업데이트
            try:
                await self._update_status()
            except Exception as e:
                logger.error(f"상태 업데이트 실패: {e}")
    
    async def _update_status(self) -> None:
        """봇 상태 메시지 업데이트"""
        try:
            # 현재 재생 중인 서버 수 계산
            playing_count = sum(
                1 for vc in self.voice_clients
                if isinstance(vc, discord.VoiceClient) and vc.is_playing()
            )
            
            # 상태 메시지 구성
            if playing_count > 0:
                status_text = f"{playing_count}개 서버에서 재생 중 🎵"
                activity_type = discord.ActivityType.playing
            else:
                total_guilds = len(self.guilds)
                status_text = f"{total_guilds}개 서버 | /play로 시작"
                activity_type = discord.ActivityType.listening
            
            await self.change_presence(
                activity=discord.Activity(
                    type=activity_type,
                    name=status_text
                )
            )
        except Exception as e:
            logger.error(f"상태 업데이트 실패: {e}")
    
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """음성 채널 상태 변경 처리"""
        if member.id != self.user.id:
            return
        
        if before.channel and not after.channel:
            guild_id = before.channel.guild.id
            
            # 실행 중인 가사 Task 취소
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
        """봇 종료 처리"""
        if self._closing:
            return
        self._closing = True
        
        try:
            logger.info("봇 종료 시작...")
            
            # 자동 저장 Task 취소
            if self._auto_save_task and not self._auto_save_task.done():
                self._auto_save_task.cancel()
                try:
                    await self._auto_save_task
                except asyncio.CancelledError:
                    pass
            
            # 상태 업데이트 Task 취소
            if self._status_update_task and not self._status_update_task.done():
                self._status_update_task.cancel()
                try:
                    await self._status_update_task
                except asyncio.CancelledError:
                    pass
            
            # 모든 가사 Task 취소
            for guild_id, task in list(self.lyrics_tasks.items()):
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            self.lyrics_tasks.clear()
            
            # 데이터 저장
            self.data_manager.save_data()
            
            # 모든 음성 연결 종료
            for vc in list(self.voice_clients):
                try:
                    if vc.is_playing():
                        vc.stop()
                    await vc.disconnect(force=True)
                except Exception as e:
                    logger.warning(f"음성 연결 종료 실패: {e}")
            
            logger.info("봇 종료 완료")
        except Exception as e:
            logger.error(f"종료 처리 실패: {e}")
        finally:
            await super().close()


def main():
    """봇 실행"""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN이 설정되지 않았습니다.")
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
    finally:
        logger.info("봇 종료됨")


if __name__ == "__main__":
    main()