import discord
import asyncio
import speech_recognition as sr
from difflib import SequenceMatcher
import tempfile
import os
import yt_dlp
import numpy as np
from utils import embed_error, embed_info, embed_success, embed_neutral
from utils.lyrics_sync import fetch_lrc

try:
    import librosa
except Exception:
    librosa = None

YTDL_STREAM_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'noplaylist': True,
}

YTDL_DOWNLOAD_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'noplaylist': True,
    'outtmpl': os.path.join(tempfile.gettempdir(), 'karaoke-%(id)s.%(ext)s')
}

FFMPEG_OPTIONS = {'options': '-vn'}


class KaraokeSession:
    def __init__(self, title: str, user_id: int, original_audio_path: str, webpage_url: str | None, channel_id: int, message_id: int | None = None):
        self.song_title = title
        self.user_id = user_id
        self.is_recording = False
        self.original_audio_path = original_audio_path  # 원곡(보컬 포함) 경로
        self.mr_audio_path = None  # MR(반주) 경로
        self.temp_user_path = None
        self.completed = False
        self.webpage_url = webpage_url
        self.channel_id = channel_id
        self.message_id = message_id


def calculate_similarity(original: str, recognized: str) -> float:
    original = original.lower().strip()
    recognized = recognized.lower().strip()
    
    if not recognized:
        return 0.0
    
    return SequenceMatcher(None, original, recognized).ratio() * 100


async def analyze_singing_full(original_audio_path: str, user_audio_path: str) -> dict:
    recognizer = sr.Recognizer()
    recognized_text = ""
    
    # 기본 점수 (노래를 불렀다는 것만으로도 기본 점수 제공)
    pitch_stability_score = 50.0
    pitch_match_score = 50.0
    energy_match_score = 50.0
    pronunciation_score = 50.0
    length_score = 50.0
    
    try:
        # 음성 인식 (실패해도 계속 진행)
        try:
            with sr.AudioFile(user_audio_path) as source:
                audio = recognizer.record(source)
                try:
                    recognized_text = recognizer.recognize_google(audio, language='ko-KR')
                    # 음성 인식 성공 시 보너스
                    if recognized_text:
                        word_count = len(recognized_text.split())
                        pronunciation_score = min(100.0, 50 + word_count * 5)
                        length_score = min(100.0, 50 + word_count * 3)
                except sr.UnknownValueError:
                    pass  # 인식 실패해도 기본 점수 유지
                except sr.RequestError:
                    pass  # API 오류도 기본 점수 유지
        except Exception:
            pass  # 파일 읽기 실패해도 계속 진행

        # librosa 분석 (사용 가능하고 성공하면 보너스)
        if librosa is not None:
            try:
                orig_y, orig_sr = librosa.load(original_audio_path, sr=22050)
                user_y, user_sr = librosa.load(user_audio_path, sr=22050)
                
                # 길이 맞추기
                min_len = min(len(orig_y), len(user_y))
                if min_len > 22050:  # 최소 1초 이상
                    orig_y = orig_y[:min_len]
                    user_y = user_y[:min_len]

                    # 음높이 분석
                    try:
                        orig_f0 = librosa.yin(orig_y, fmin=80, fmax=1000, sr=orig_sr)
                        user_f0 = librosa.yin(user_y, fmin=80, fmax=1000, sr=user_sr)
                        orig_f0 = orig_f0[~np.isnan(orig_f0)]
                        user_f0 = user_f0[~np.isnan(user_f0)]
                        
                        if len(user_f0) > 10:
                            mean_user = np.mean(user_f0)
                            std_user = np.std(user_f0)
                            if mean_user > 0:
                                variability = (std_user / mean_user) * 100
                                # 안정성: 변동성이 낮을수록 높은 점수
                                pitch_stability_score = max(50.0, min(100.0, 100 - variability))
                        
                        if len(orig_f0) > 10 and len(user_f0) > 10:
                            mean_orig = np.mean(orig_f0)
                            mean_user = np.mean(user_f0)
                            diff = abs(mean_orig - mean_user)
                            # 피치 매칭: 차이가 50Hz 이내면 만점, 200Hz 이상이면 기본점수
                            pitch_match_score = max(50.0, min(100.0, 100 - (diff / 2)))
                    except Exception:
                        pass  # 피치 분석 실패 시 기본 점수 유지

                    # 에너지 분석
                    try:
                        orig_rms = librosa.feature.rms(y=orig_y)[0]
                        user_rms = librosa.feature.rms(y=user_y)[0]
                        min_frames = min(len(orig_rms), len(user_rms))
                        
                        if min_frames > 10:
                            # 상관계수 계산
                            corr_matrix = np.corrcoef(orig_rms[:min_frames], user_rms[:min_frames])
                            if not np.isnan(corr_matrix[0, 1]):
                                corr = corr_matrix[0, 1]
                                # 상관계수를 점수로 변환 (-1~1 -> 50~100)
                                energy_match_score = max(50.0, min(100.0, 50 + (corr * 50)))
                    except Exception:
                        pass  # 에너지 분석 실패 시 기본 점수 유지
            except Exception:
                pass  # librosa 로드 실패 시 기본 점수 유지

        # 종합 점수 계산 (기본 50점 + 보너스)
        total_score = (
            pitch_stability_score * 0.25 +
            pitch_match_score * 0.25 +
            energy_match_score * 0.20 +
            pronunciation_score * 0.15 +
            length_score * 0.15
        )
        
        return {
            'success': True,
            'recognized_text': recognized_text or "음성 인식 실패 (기본 점수 적용)",
            'pitch_stability_score': round(pitch_stability_score, 1),
            'pitch_match_score': round(pitch_match_score, 1),
            'energy_match_score': round(energy_match_score, 1),
            'pronunciation_score': round(pronunciation_score, 1),
            'length_score': round(length_score, 1),
            'total_score': round(total_score, 1),
            'grade': get_grade(total_score)
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'분석 중 오류 발생: {str(e)}'
        }


def get_grade(score: float) -> str:
    """점수에 따른 등급 반환 (50점 기본점수 기준 조정)"""
    if score >= 90:
        return "S"
    elif score >= 85:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 75:
        return "B+"
    elif score >= 70:
        return "B"
    elif score >= 65:
        return "C+"
    elif score >= 60:
        return "C"
    elif score >= 55:
        return "D+"
    else:
        return "D"


@discord.slash_command(name="노래방", description="씩씩이 노래방 모드")
async def karaoke(
    ctx: discord.ApplicationContext,
    제목_또는_url: str = discord.Option(str, description="노래의 제목이나 URL"),
    instrumental: bool = discord.Option(bool, description="검색어일 때 반주(Instrumental) 보정", default=False)
):
    if not ctx.author.voice:
        await ctx.respond(embed=embed_error("음성 채널에 먼저 참가해주세요"), ephemeral=True)
        return
    
    guild_id = ctx.guild.id
    
    if guild_id in ctx.bot.karaoke_sessions:
        await ctx.respond(embed=embed_error("이미 진행 중인 노래방 세션이 있습니다"), ephemeral=True)
        return
    
    await ctx.defer()
    # MR(반주) 버전 다운로드
    mr_query = 제목_또는_url if 제목_또는_url.startswith("http") else f"{제목_또는_url} instrumental"
    try:
        with yt_dlp.YoutubeDL(YTDL_DOWNLOAD_OPTIONS) as ydl:
            data = ydl.extract_info(mr_query, download=True)
            if 'entries' in data:
                entries = [e for e in data.get('entries', []) if e]
                if not entries:
                    raise ValueError("MR(반주) 검색 결과가 없습니다")
                data = entries[0]
            mr_title = data.get('title')
            mr_webpage_url = data.get('webpage_url') or data.get('url')
            mr_audio_path = ydl.prepare_filename(data)
    except Exception as e:
        await ctx.followup.send(embed=embed_error(f"MR(반주) 다운로드 실패: {str(e)}"), ephemeral=True)
        return
    # 원곡(보컬 포함) 버전 다운로드
    original_query = 제목_또는_url if 제목_또는_url.startswith("http") else 제목_또는_url
    try:
        with yt_dlp.YoutubeDL(YTDL_DOWNLOAD_OPTIONS) as ydl:
            data = ydl.extract_info(original_query, download=True)
            if 'entries' in data:
                entries = [e for e in data.get('entries', []) if e]
                if not entries:
                    raise ValueError("원곡(보컬 포함) 검색 결과가 없습니다")
                data = entries[0]
            original_title = data.get('title')
            original_webpage_url = data.get('webpage_url') or data.get('url')
            original_audio_path = ydl.prepare_filename(data)
    except Exception as e:
        await ctx.followup.send(embed=embed_error(f"원곡(보컬 포함) 다운로드 실패: {str(e)}"), ephemeral=True)
        return

    # 초기 임베드 전송 후 메시지 저장
    # 메시지를 먼저 만들기 위해 아래에서 생성 후 세션 구성
    title_link = f"[{mr_title or mr_query}]({mr_webpage_url})" if mr_webpage_url else f"**{mr_title or mr_query}**"
    embed = embed_info(f"{title_link}\n반주(MR) 버전이 재생되며 전체 구간을 녹음합니다.", title="🎤 전체 곡 노래방 모드")
    embed.add_field(name="📝 안내", value="• 반주 시작과 함께 녹음 시작\n• 재생 종료 또는 `/노래방_중지` 시 채점\n• 피치 안정성/피치 매칭/에너지/발음 기반 종합 점수", inline=False)
    first_message = await ctx.followup.send(embed=embed)

    # 세션에 MR/원곡 경로 모두 저장
    session = KaraokeSession(mr_title or mr_query, ctx.author.id, original_audio_path, mr_webpage_url, ctx.channel_id, first_message.id)
    session.mr_audio_path = mr_audio_path
    session.original_audio_path = original_audio_path
    ctx.bot.karaoke_sessions[guild_id] = session
    
    try:
        channel = ctx.author.voice.channel
        voice_client = ctx.guild.voice_client
        
        if not voice_client:
            voice_client = await channel.connect()
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)
        
        session.is_recording = True
        async def recording_finished_callback(sink, *args):
            return
        voice_client.start_recording(discord.sinks.WaveSink(), recording_finished_callback)
        def after_play(err):
            fut = asyncio.run_coroutine_threadsafe(finish_karaoke(ctx.guild.id, ctx.bot), ctx.bot.loop)
            try:
                fut.result()
            except Exception:
                pass
        initial_volume = ctx.bot.data_manager.get_guild_volume(guild_id) / 100 if hasattr(ctx.bot, 'data_manager') else 0.05
        source = discord.FFmpegPCMAudio(session.mr_audio_path, **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=initial_volume)
        voice_client.play(source, after=after_play)
        lyrics = await fetch_lrc(mr_title or mr_query)
        if lyrics:
            lyrics_msg = await ctx.followup.send(embed=embed_info("싱크 가사 준비 중..."))
            async def send_lyrics():
                start_time = asyncio.get_event_loop().time()
                for t, line in lyrics:
                    now = asyncio.get_event_loop().time()
                    wait_sec = t - (now - start_time)
                    if wait_sec > 0:
                        await asyncio.sleep(wait_sec)
                    await lyrics_msg.edit(embed=embed_info(line))
            asyncio.create_task(send_lyrics())
        else:
            await ctx.followup.send(embed=embed_info("싱크 가사를 찾을 수 없습니다."))
    
    except Exception as e:
        del ctx.bot.karaoke_sessions[guild_id]
        await ctx.followup.send(embed=embed_error(f"노래방 세션 시작 실패: {str(e)}"), ephemeral=True)


async def finish_karaoke(guild_id: int, client: discord.Client):
    if guild_id not in client.karaoke_sessions:
        return
    session = client.karaoke_sessions[guild_id]
    if session.completed:
        return
    session.completed = True
    guild = client.get_guild(guild_id)
    if not guild:
        return
    voice_client = guild.voice_client
    if not voice_client:
        return
    try:
        voice_client.stop_recording()
        await asyncio.sleep(1)
        if hasattr(voice_client, 'sink') and voice_client.sink:
            user_audio = voice_client.sink.audio_data.get(session.user_id)
            if not user_audio:
                channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                if channel:
                    await channel.send(embed=discord.Embed(description="녹음 실패", color=0xe74c3c))
                del client.karaoke_sessions[guild_id]
                return
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_file.write(user_audio.file.getvalue())
                user_path = tmp_file.name
            session.temp_user_path = user_path
            try:
                # MR이 아닌 원곡(보컬 포함) 경로로 채점
                result = await analyze_singing_full(session.original_audio_path, user_path)
                channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                if result['success']:
                    # 원본 메시지에 답장
                    channel = guild.get_channel(session.channel_id) or guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                    
                    # 점수에 따른 색상
                    score = result['total_score']
                    if score >= 80:
                        color = 0x2ECC71  # 초록 (A 이상)
                    elif score >= 70:
                        color = 0xF39C12  # 주황 (B)
                    elif score >= 60:
                        color = 0x3498DB  # 파랑 (C)
                    else:
                        color = 0x95A5A6  # 회색 (D)
                    
                    embed = discord.Embed(
                        title="🎤 전체 곡 채점 결과",
                        description=f"[{session.song_title}]({session.webpage_url})" if session.webpage_url else f"**{session.song_title}**",
                        color=color
                    )
                    embed.add_field(name="🎵 피치 안정성", value=f"{result['pitch_stability_score']}점", inline=True)
                    embed.add_field(name="🎯 피치 매칭", value=f"{result['pitch_match_score']}점", inline=True)
                    embed.add_field(name="⚡ 에너지 매칭", value=f"{result['energy_match_score']}점", inline=True)
                    embed.add_field(name="🗣️ 발음 점수", value=f"{result['pronunciation_score']}점", inline=True)
                    embed.add_field(name="📏 길이 점수", value=f"{result['length_score']}점", inline=True)
                    embed.add_field(name="\u200b", value="\u200b", inline=True)  # 빈 칸
                    embed.add_field(name="📊 최종 점수", value=f"# **{result['total_score']}점 ({result['grade']})**", inline=False)
                    if result['recognized_text'] and "음성 인식 실패" not in result['recognized_text']:
                        embed.add_field(name="🎙️ 인식된 가사", value=f"```{result['recognized_text'][:100]}```", inline=False)
                    embed.set_footer(text="실험적 채점 • 기본 50점 + 분석 보너스")
                    if channel and session.message_id:
                        try:
                            original = await channel.fetch_message(session.message_id)
                            await original.reply(embed=embed)
                        except Exception:
                            await channel.send(embed=embed)
                else:
                    channel = guild.get_channel(session.channel_id) or guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                    if channel:
                        fail_embed = discord.Embed(description=f"채점 실패: {result.get('error')}", color=0xe74c3c)
                        if session.message_id:
                            try:
                                original = await channel.fetch_message(session.message_id)
                                await original.reply(embed=fail_embed)
                            except Exception:
                                await channel.send(embed=fail_embed)
            finally:
                if os.path.exists(session.temp_user_path):
                    os.unlink(session.temp_user_path)
                del client.karaoke_sessions[guild_id]
    except Exception:
        del client.karaoke_sessions[guild_id]


@discord.slash_command(name="노래방_중지", description="노래방 녹음을 중지하고 채점합니다")
async def karaoke_stop(ctx: discord.ApplicationContext):
    guild_id = ctx.guild.id
    
    if guild_id not in ctx.bot.karaoke_sessions:
        await ctx.respond(embed=embed_error("진행 중인 노래방 세션이 없습니다"), ephemeral=True)
        return
    
    session = ctx.bot.karaoke_sessions[guild_id]
    
    if session.user_id != ctx.author.id:
        await ctx.respond(embed=embed_error("노래방 세션을 시작한 사용자만 중지할 수 있습니다"), ephemeral=True)
        return
    
    await ctx.defer()
    
    voice_client = ctx.guild.voice_client
    
    if not voice_client:
        del ctx.bot.karaoke_sessions[guild_id]
        await ctx.followup.send(embed=embed_error("음성 연결이 끊어졌습니다"))
        return
    
    # 재생 도중 강제 종료 채점
    try:
        voice_client.stop_recording()
        await asyncio.sleep(1)
        if hasattr(voice_client, 'sink') and voice_client.sink:
            user_audio = voice_client.sink.audio_data.get(ctx.author.id)
            if not user_audio:
                await ctx.followup.send(embed=embed_error("녹음된 음성을 찾을 수 없습니다"))
                del ctx.bot.karaoke_sessions[guild_id]
                return
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_file.write(user_audio.file.getvalue())
                user_path = tmp_file.name
            try:
                result = await analyze_singing_full(session.original_audio_path, user_path)
                if result['success']:
                    channel = ctx.guild.get_channel(session.channel_id) or ctx.channel
                    embed = embed_success(f"[{session.song_title}]({session.webpage_url})" if session.webpage_url else f"**{session.song_title}**", title="🎤 전체 곡 채점 결과(수동 종료)")
                    embed.add_field(name="🗣️ 발음/길이", value=f"{result['pronunciation_score']}/{result['length_score']}", inline=True)
                    embed.add_field(name="🎵 피치 안정성", value=f"{result['pitch_stability_score']}", inline=True)
                    embed.add_field(name="🎯 피치 매칭", value=f"{result['pitch_match_score']}", inline=True)
                    embed.add_field(name="⚡ 에너지 매칭", value=f"{result['energy_match_score']}", inline=True)
                    embed.add_field(name="📊 최종 점수", value=f"**{result['total_score']}점 ({result['grade']})**", inline=False)
                    if result['recognized_text']:
                        embed.add_field(name="인식된 일부", value=f"```{result['recognized_text'][:120]}```", inline=False)
                    embed.set_footer(text=f"부른 사람: {ctx.author.display_name}")
                    if session.message_id:
                        try:
                            original = await channel.fetch_message(session.message_id)
                            await original.reply(embed=embed)
                        except Exception:
                            await ctx.followup.send(embed=embed)
                    else:
                        await ctx.followup.send(embed=embed)
                else:
                    fail_embed = embed_error(f"채점 실패: {result.get('error')}")
                    if session.message_id:
                        try:
                            original = await channel.fetch_message(session.message_id)
                            await original.reply(embed=fail_embed)
                        except Exception:
                            await ctx.followup.send(embed=fail_embed)
                    else:
                        await ctx.followup.send(embed=fail_embed)
            finally:
                if os.path.exists(user_path):
                    os.unlink(user_path)
        else:
            await ctx.followup.send(embed=embed_error("녹음 데이터를 찾을 수 없습니다"))
    except Exception as e:
        await ctx.followup.send(embed=embed_error(f"채점 중 오류 발생: {str(e)}"))
    finally:
        del ctx.bot.karaoke_sessions[guild_id]


def setup(bot):
    bot.add_application_command(karaoke)
    bot.add_application_command(karaoke_stop)
