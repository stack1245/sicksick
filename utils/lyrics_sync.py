"""노래방 기능용 가사 동기화"""
from __future__ import annotations
import re
from typing import Optional, List, Tuple
import aiohttp

__all__ = ["parse_lrc", "fetch_lrc"]

LRC_TIMESTAMP = re.compile(r"\[(\d+):(\d+)(?:\.(\d+))?\]")


def parse_lrc(lrc_text: str) -> List[Tuple[float, str]]:
    """LRC 형식 가사를 타임스탬프가 있는 라인으로 파싱"""
    lyrics = []
    for line in lrc_text.splitlines():
        matches = list(LRC_TIMESTAMP.finditer(line))
        if not matches:
            continue
        
        text = LRC_TIMESTAMP.sub("", line).strip()
        for m in matches:
            min_, sec, ms = m.groups()
            time = int(min_) * 60 + int(sec)
            if ms:
                time += int(ms) / 100
            lyrics.append((time, text))
    
    lyrics.sort()
    return lyrics


async def fetch_lrc(song_title: str, artist: Optional[str] = None) -> Optional[List[Tuple[float, str]]]:
    """온라인 데이터베이스에서 동기화된 가사 가져오기"""
    search_query = song_title.replace(" ", "+")
    url = f"https://raw.githubusercontent.com/lrcdb/lrcdb/master/lrc/{search_query}.lrc"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                lrc_text = await resp.text()
                return parse_lrc(lrc_text)
    
    return None
