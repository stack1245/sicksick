"""씩씩이 음악 봇 데이터 관리자"""
from __future__ import annotations
import json
from pathlib import Path
from typing import TYPE_CHECKING

from .data_health_checker import create_health_checker

if TYPE_CHECKING:
    import discord

__all__ = ["DataManager"]


class DataManager:
    """재생목록 및 설정 영구 저장 관리"""
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.data_dir = Path(__file__).parent.parent / "data"
        self.playlists_file = self.data_dir / "playlists.json"
        self.settings_file = self.data_dir / "settings.json"
        
        self.data_dir.mkdir(exist_ok=True)
        self.health_checker = create_health_checker("Music")
        self._perform_health_check()
        
        self.bot.playlists = {}
        self.bot.guild_settings = {}
        self.bot.save_data = self.save_data
        self.bot.load_data = self.load_data
    
    def _perform_health_check(self) -> None:
        """데이터 파일 검사 및 복구"""
        files = [str(self.playlists_file), str(self.settings_file)]
        self.health_checker.health_check_and_repair(files)
    
    def save_data(self) -> None:
        self.save_playlists()
        self.save_settings()
    
    def load_data(self) -> None:
        self.load_playlists()
        self.load_settings()
    
    def save_playlists(self) -> None:
        with open(self.playlists_file, "w", encoding="utf-8") as f:
            json.dump(self.bot.playlists, f, indent=2, ensure_ascii=False)
    
    def load_playlists(self) -> None:
        if not self.playlists_file.exists():
            self.bot.playlists = {}
            self.save_playlists()
            return
        
        with open(self.playlists_file, "r", encoding="utf-8") as f:
            self.bot.playlists = json.load(f)
    
    def save_settings(self) -> None:
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(self.bot.guild_settings, f, indent=2, ensure_ascii=False)
    
    def load_settings(self) -> None:
        if not self.settings_file.exists():
            self.bot.guild_settings = {}
            self.save_settings()
            return
        
        with open(self.settings_file, "r", encoding="utf-8") as f:
            self.bot.guild_settings = json.load(f)
    
    def get_guild_volume(self, guild_id: int) -> int:
        """서버 볼륨 설정 조회"""
        settings = self.bot.guild_settings.get(str(guild_id), {})
        return settings.get("volume", 5)
    
    def set_guild_volume(self, guild_id: int, volume: int) -> None:
        """서버 볼륨 설정 저장"""
        if str(guild_id) not in self.bot.guild_settings:
            self.bot.guild_settings[str(guild_id)] = {}
        self.bot.guild_settings[str(guild_id)]["volume"] = volume
        self.save_settings()
