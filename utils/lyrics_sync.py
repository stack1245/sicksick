"""노래방 기능용 가사 동기화"""
from __future__ import annotations
import re
import logging
from typing import Optional, List, Tuple
import aiohttp

__all__ = ["parse_lrc", "fetch_lrc"]

logger = logging.getLogger(__name__)

LRC_TIMESTAMP = re.compile(r"\[(\d+):(\d+)(?:\.(\d+))?\]")


def parse_lrc(lrc_text: str) -> List[Tuple[float, str]]:
    """LRC 형식 가사를 타임스탬프가 있는 라인으로 파싱"""
    lyrics = []
    for line in lrc_text.splitlines():
        matches = list(LRC_TIMESTAMP.finditer(line))
        if not matches:
            continue
        
        text = LRC_TIMESTAMP.sub("", line).strip()
        if not text:  # 빈 줄 건너뛰기
            continue
        
        for m in matches:
            min_, sec, ms = m.groups()
            time = int(min_) * 60 + int(sec)
            if ms:
                time += int(ms.ljust(3, '0')[:3]) / 1000
            lyrics.append((time, text))
    
    lyrics.sort()
    return lyrics


async def fetch_lrc(song_title: str, artist: Optional[str] = None) -> Optional[List[Tuple[float, str]]]:
    """온라인 데이터베이스에서 동기화된 가사 가져오기"""
    # LRCLIB API 사용 (무료, 안정적)
    try:
        async with aiohttp.ClientSession() as session:
            # 검색 쿼리 생성
            params = {"track_name": song_title}
            if artist:
                params["artist_name"] = artist
            
            # LRCLIB API 호출
            async with session.get("https://lrclib.net/api/get", params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # syncedLyrics 필드에서 LRC 가져오기
                    synced_lyrics = data.get("syncedLyrics")
                    if synced_lyrics:
                        logger.info(f"가사 찾음: {song_title}")
                        return parse_lrc(synced_lyrics)
                    else:
                        logger.warning(f"동기화된 가사 없음: {song_title}")
                else:
                    logger.warning(f"LRCLIB API 오류: {resp.status}")
            
            # LRCLIB 검색 API 시도 (정확한 매칭 실패 시)
            async with session.get("https://lrclib.net/api/search", params=params) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    if results and len(results) > 0:
                        first_result = results[0]
                        synced_lyrics = first_result.get("syncedLyrics")
                        if synced_lyrics:
                            logger.info(f"가사 찾음 (검색): {song_title}")
                            return parse_lrc(synced_lyrics)
    
    except Exception as e:
        logger.error(f"가사 가져오기 실패: {e}")
    
    return None
