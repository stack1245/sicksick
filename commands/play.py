import discord
import yt_dlp
import asyncio
import logging
from utils import embed_error, embed_success, embed_info
from utils.lyrics_sync import fetch_lrc

logger = logging.getLogger(__name__)

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "extractaudio": True,
    "audioformat": "mp3",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "referer": "https://www.youtube.com/",
    "socket_timeout": 30,
    "retries": 10,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -bufsize 512k"
}


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.05):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("url")
        self.webpage_url = data.get("webpage_url", data.get("url"))
        self.duration = data.get("duration")
        self.thumbnail = data.get("thumbnail")
        self.uploader = data.get("uploader")
        self.view_count = data.get("view_count")
    
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            
            if "entries" in data:
                if not data["entries"]:
                    raise ValueError("검색 결과가 없습니다")
                data = data["entries"][0]
            
            filename = data["url"]
            return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)
    
    @classmethod
    async def create_source(cls, search, *, loop=None):
        """검색어나 URL로부터 소스 정보만 추출 (스트림 URL은 나중에)"""
        loop = loop or asyncio.get_event_loop()
        
        try:
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(search, download=False))
                
                if "entries" in data:
                    if not data["entries"]:
                        raise ValueError("검색 결과가 없습니다")
                    data = data["entries"][0]
                
                return {
                    "webpage_url": data.get("webpage_url"),
                    "title": data.get("title"),
                    "duration": data.get("duration"),
                    "thumbnail": data.get("thumbnail"),
                    "uploader": data.get("uploader"),
                    "view_count": data.get("view_count"),
                }
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "Private video" in error_msg:
                raise ValueError("비공개 비디오입니다. 접근할 수 없습니다.")
            elif "Video unavailable" in error_msg:
                raise ValueError("비디오를 사용할 수 없습니다.")
            elif "This video is not available" in error_msg:
                raise ValueError("이 비디오는 사용할 수 없습니다.")
            elif "members-only content" in error_msg:
                raise ValueError("멤버십 전용 콘텐츠입니다.")
            elif "blocked" in error_msg.lower():
                raise ValueError("이 비디오는 차단되었거나 지역 제한이 있습니다.")
            else:
                raise ValueError(f"비디오를 불러올 수 없습니다: {error_msg}")
    
    @classmethod
    async def prepare_player(cls, source_info, *, loop=None, volume=0.05):
        """재생 직전에 새로운 스트림 URL을 가져와서 플레이어 생성"""
        loop = loop or asyncio.get_event_loop()
        
        try:
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                data = await loop.run_in_executor(
                    None, lambda: ydl.extract_info(source_info["webpage_url"], download=False)
                )
                
                if "entries" in data:
                    if not data["entries"]:
                        raise ValueError("검색 결과가 없습니다")
                    data = data["entries"][0]
                
                # source_info의 정보를 유지하면서 새로운 스트림 URL 사용
                data.update(source_info)
                filename = data["url"]
                
                return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data, volume=volume)
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "Private video" in error_msg:
                raise ValueError("비공개 비디오입니다. 접근할 수 없습니다.")
            elif "Video unavailable" in error_msg:
                raise ValueError("비디오를 사용할 수 없습니다.")
            elif "This video is not available" in error_msg:
                raise ValueError("이 비디오는 사용할 수 없습니다.")
            elif "members-only content" in error_msg:
                raise ValueError("멤버십 전용 콘텐츠입니다.")
            elif "blocked" in error_msg.lower():
                raise ValueError("이 비디오는 차단되었거나 지역 제한이 있습니다.")
            else:
                raise ValueError(f"비디오를 불러올 수 없습니다: {error_msg}")


@discord.slash_command(name="재생", description="노래를 재생합니다")
async def play(
    ctx: discord.ApplicationContext,
    제목_또는_url: str = discord.Option(str, "노래의 제목이나 URL")
):
    if not ctx.author.voice:
        await ctx.respond(
            embed=discord.Embed(description="음성 채널에 먼저 참가해주세요", color=0xe74c3c),
            ephemeral=True
        )
        return
    
    await ctx.defer()
    
    try:
        channel = ctx.author.voice.channel
        voice_client = ctx.guild.voice_client
        
        # 음성 클라이언트 연결 상태 확인 및 처리
        if not voice_client or not voice_client.is_connected():
            if voice_client:
                try:
                    if voice_client.is_playing():
                        voice_client.stop()
                    await voice_client.disconnect(force=True)
                except Exception as e:
                    logger.warning(f"기존 연결 해제 중 오류 (무시됨): {e}")
                # 연결 해제 후 대기
                await asyncio.sleep(0.5)
            try:
                voice_client = await channel.connect(timeout=15.0, reconnect=True)
                # 연결 후 안정화 대기
                await asyncio.sleep(0.3)
            except asyncio.TimeoutError:
                await ctx.followup.send(embed=embed_error("음성 채널 연결 시간 초과"))
                return
            except discord.ClientException as e:
                if "already connected" in str(e).lower():
                    # 이미 연결되어 있다면 기존 연결 사용
                    voice_client = ctx.guild.voice_client
                    if not voice_client:
                        await ctx.followup.send(embed=embed_error("음성 연결 상태 불일치"))
                        return
                else:
                    await ctx.followup.send(embed=embed_error(f"음성 채널 연결 실패: {str(e)}"))
                    return
            except Exception as e:
                await ctx.followup.send(embed=embed_error(f"음성 채널 연결 실패: {str(e)}"))
                return
        elif voice_client.channel != channel:
            # 다른 채널에 연결되어 있으면 이동
            try:
                await voice_client.move_to(channel)
            except Exception as e:
                logger.warning(f"채널 이동 실패, 재연결 시도: {e}")
                try:
                    if voice_client.is_playing():
                        voice_client.stop()
                    await voice_client.disconnect(force=True)
                    await asyncio.sleep(0.5)
                    voice_client = await channel.connect(timeout=15.0, reconnect=True)
                    await asyncio.sleep(0.3)
                except Exception as reconnect_error:
                    await ctx.followup.send(embed=embed_error(f"재연결 실패: {str(reconnect_error)}"))
                    return
        
        # 먼저 소스 정보만 추출
        source_info = await YTDLSource.create_source(제목_또는_url, loop=ctx.bot.loop)
        guild_id = ctx.guild.id
        
        if guild_id not in ctx.bot.music_queues:
            ctx.bot.music_queues[guild_id] = []
        
        if voice_client.is_playing():
            # 대기열에는 소스 정보만 저장
            ctx.bot.music_queues[guild_id].append(source_info)
            embed = embed_info("", title="🎵 재생목록에 추가")
            embed.add_field(name="제목", value=f"[{source_info['title']}]({source_info['webpage_url']})", inline=False)
        else:
            # 재생 직전에 플레이어 생성
            initial_volume = ctx.bot.data_manager.get_guild_volume(guild_id) / 100 if hasattr(ctx.bot, 'data_manager') else 0.05
            player = await YTDLSource.prepare_player(source_info, loop=ctx.bot.loop, volume=initial_volume)
            
            def after_playing(error):
                if error:
                    logger.error(f"재생 중 오류 발생: {error}")
                asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop)
            
            voice_client.play(player, after=after_playing)
            ctx.bot.now_playing[guild_id] = player
            embed = embed_success("", title="🎶 재생 중")
            embed.add_field(name="제목", value=f"[{source_info['title']}]({source_info['webpage_url']})", inline=False)

            # 싱크 가사 표시 (LRC)
            lyrics = await fetch_lrc(source_info['title'])
            if lyrics:
                lyrics_msg = await ctx.followup.send(embed=embed_info("싱크 가사 준비 중..."))
                async def send_lyrics():
                    try:
                        start_time = asyncio.get_event_loop().time()
                        for t, line in lyrics:
                            now = asyncio.get_event_loop().time()
                            wait_sec = t - (now - start_time)
                            if wait_sec > 0:
                                await asyncio.sleep(wait_sec)
                            try:
                                await lyrics_msg.edit(embed=embed_info(line))
                            except discord.NotFound:
                                logger.debug("가사 메시지가 삭제됨")
                                break
                            except Exception as e:
                                logger.warning(f"가사 업데이트 오류: {e}")
                                break
                    except asyncio.CancelledError:
                        logger.debug("가사 Task 취소됨")
                    except Exception as e:
                        logger.error(f"가사 표시 오류: {e}")
                
                # Task 추적 - 이전 Task가 있으면 취소
                if guild_id in ctx.bot.lyrics_tasks:
                    old_task = ctx.bot.lyrics_tasks[guild_id]
                    if not old_task.done():
                        old_task.cancel()
                
                ctx.bot.lyrics_tasks[guild_id] = asyncio.create_task(send_lyrics())
            else:
                await ctx.followup.send(embed=embed_info("싱크 가사를 찾을 수 없습니다."))
        
        # 재생시간 정보
        if source_info.get('duration'):
            minutes, seconds = divmod(source_info['duration'], 60)
            embed.add_field(name="⏱️ 재생시간", value=f"{int(minutes)}:{int(seconds):02d}", inline=True)
        
        # 업로더 정보
        if source_info.get('uploader'):
            embed.add_field(name="👤 업로더", value=source_info['uploader'], inline=True)
        
        # 조회수 정보
        if source_info.get('view_count'):
            views = source_info['view_count']
            if views >= 1000000:
                view_str = f"{views/1000000:.1f}M"
            elif views >= 1000:
                view_str = f"{views/1000:.1f}K"
            else:
                view_str = str(views)
            embed.add_field(name="👁️ 조회수", value=view_str, inline=True)
        
        # 요청자 정보
        embed.set_footer(text=f"요청자: {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        
        if source_info.get('thumbnail'):
            embed.set_thumbnail(url=source_info['thumbnail'])
        await ctx.followup.send(embed=embed)
    
    except ValueError as e:
        await ctx.followup.send(embed=embed_error(str(e)))
    except Exception as e:
        import traceback
        error_msg = f"오류 발생: {str(e)}"
        logger.error(f"Play command error: {traceback.format_exc()}")
        await ctx.followup.send(embed=embed_error(error_msg))


async def play_next(ctx):
    guild_id = ctx.guild.id
    voice_client = ctx.guild.voice_client
    
    if not voice_client:
        logger.debug(f"Guild {guild_id}: 음성 클라이언트 없음, 재생 종료")
        ctx.bot.now_playing.pop(guild_id, None)
        # 가사 Task 정리
        if guild_id in ctx.bot.lyrics_tasks:
            task = ctx.bot.lyrics_tasks.pop(guild_id)
            if not task.done():
                task.cancel()
        return
    
    # 연결 상태 확인
    if not voice_client.is_connected():
        logger.warning(f"Guild {guild_id}: 음성 연결이 끊어짐, 재생 종료")
        ctx.bot.music_queues.pop(guild_id, None)
        ctx.bot.now_playing.pop(guild_id, None)
        # 가사 Task 정리
        if guild_id in ctx.bot.lyrics_tasks:
            task = ctx.bot.lyrics_tasks.pop(guild_id)
            if not task.done():
                task.cancel()
        return
    
    # 반복 모드 확인
    loop_mode = ctx.bot.loop_mode.get(guild_id, "off") if hasattr(ctx.bot, 'loop_mode') else "off"
    
    # 현재 곡 반복 모드
    if loop_mode == "one" and guild_id in ctx.bot.now_playing:
        current_song_data = {
            'webpage_url': ctx.bot.now_playing[guild_id].webpage_url,
            'title': ctx.bot.now_playing[guild_id].title,
            'duration': ctx.bot.now_playing[guild_id].duration,
            'thumbnail': ctx.bot.now_playing[guild_id].thumbnail,
            'uploader': getattr(ctx.bot.now_playing[guild_id], 'uploader', None),
            'view_count': getattr(ctx.bot.now_playing[guild_id], 'view_count', None),
        }
        source_info = current_song_data
    elif guild_id in ctx.bot.music_queues and ctx.bot.music_queues[guild_id]:
        source_info = ctx.bot.music_queues[guild_id].pop(0)
        
        # 대기열 반복 모드 - 재생한 곡을 대기열 끝에 추가
        if loop_mode == "all":
            ctx.bot.music_queues[guild_id].append(source_info.copy())
    else:
        source_info = None
    
    if source_info:
        try:
            # 이전 가사 Task 취소
            if guild_id in ctx.bot.lyrics_tasks:
                old_task = ctx.bot.lyrics_tasks.pop(guild_id)
                if not old_task.done():
                    old_task.cancel()
            
            # 재생 직전에 새로운 스트림 URL로 플레이어 생성
            initial_volume = ctx.bot.data_manager.get_guild_volume(guild_id) / 100 if hasattr(ctx.bot, 'data_manager') else 0.05
            player = await YTDLSource.prepare_player(source_info, loop=ctx.bot.loop, volume=initial_volume)
            
            def after_playing(error):
                if error:
                    logger.error(f"재생 중 오류 발생: {error}")
                try:
                    asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop)
                except Exception as e:
                    logger.error(f"다음 곡 예약 실패: {e}")
            
            voice_client.play(player, after=after_playing)
            ctx.bot.now_playing[guild_id] = player
            logger.debug(f"Guild {guild_id}: 다음 곡 재생 시작 - {source_info['title']}")
            
            # 봇 상태 업데이트
            try:
                asyncio.create_task(ctx.bot._update_status())
            except Exception as e:
                logger.error(f"상태 업데이트 실패: {e}")
        except Exception as e:
            import traceback
            logger.error(f"다음 곡 재생 중 오류: {e}\n{traceback.format_exc()}")
            # 오류 발생 시 대기열의 다음 곡 재생 시도
            await play_next(ctx)
    else:
        logger.info(f"Guild {guild_id}: 대기열 비어있음, 음성 채널에서 나가기")
        ctx.bot.now_playing.pop(guild_id, None)
        # 가사 Task 정리
        if guild_id in ctx.bot.lyrics_tasks:
            task = ctx.bot.lyrics_tasks.pop(guild_id)
            if not task.done():
                task.cancel()
        
        # 음성 채널에서 나가기
        try:
            if voice_client.is_playing():
                voice_client.stop()
            await voice_client.disconnect(force=False)
            logger.info(f"Guild {guild_id}: 음성 채널에서 나감")
            
            # 봇 상태 업데이트
            try:
                await ctx.bot._update_status()
            except Exception as e:
                logger.error(f"상태 업데이트 실패: {e}")
        except Exception as e:
            logger.error(f"음성 채널 나가기 실패: {e}")


def setup(bot):
    bot.add_application_command(play)
