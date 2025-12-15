
# SickSick Music Bot 🎵

음성 채널에서 음악 재생, 대기열 관리, 노래방(MR/원곡 비교 채점), 싱크가사(LRC) 실시간 표시 기능을 제공하는 Discord 뮤직봇입니다.

## ✨ 주요 기능
- 🎶 YouTube/URL 음악 재생 및 대기열 관리
- 📝 싱크가사(LRC) 자동 검색 및 실시간 표시
- 🔁 반복 재생 모드 (현재곡/대기열)
- 🎚️ 볼륨 조절 및 설정 저장
- 🎤 노래방 모드: MR(반주) 재생 + 원곡 비교 채점
- 🇰🇷 한글 명령어 지원
- 🔄 자동 연결/재연결 및 안정적인 오류 처리
- 📤 노래 끝나면 자동으로 음성 채널 나가기

## 📋 명령어

### ▶️ 재생 명령어
| 명령어 | 설명 |
|--------|------|
| `/재생 <제목/URL>` | 음악 재생 또는 대기열에 추가 (싱크가사 자동 표시) |
| `/일시정지` | 재생/일시정지 토글 |
| `/건너뛰기` | 현재 곡 건너뛰기 |
| `/중지` | 재생 중지 및 음성 채널 나가기 |

### 📋 대기열 관리
| 명령어 | 설명 |
|--------|------|
| `/대기열` | 현재 대기열 확인 |
| `/대기열초기화` | 대기열의 모든 노래 삭제 |
| `/삭제 <번호>` | 대기열에서 특정 곡 삭제 |
| `/섞기` | 대기열 순서를 무작위로 섞기 |

### 🎚️ 재생 설정
| 명령어 | 설명 |
|--------|------|
| `/볼륨 [0-100]` | 볼륨 조절 (값 없으면 현재 볼륨 표시) |
| `/반복 <모드>` | 반복 모드 설정 (끄기/현재곡/대기열) |
| `/현재재생` | 현재 재생 중인 노래 정보 |

### 🔊 연결
| 명령어 | 설명 |
|--------|------|
| `/연결` | 음성 채널에 연결 |

### 🎤 노래방
| 명령어 | 설명 |
|--------|------|
| `/노래방 <제목/URL>` | 노래방 MR 재생 + 원곡 비교 채점 + 싱크가사 표시 |
| `/노래방정지` | 노래방 녹음 종료 및 채점 |

### ℹ️ 기타
| 명령어 | 설명 |
|--------|------|
| `/도움말` | 봇 사용법 확인 |

## 설치 및 실행
```bash
pip install -r requirements.txt
```

FFmpeg 설치: https://www.ffmpeg.org/download.html (설치 후 PATH 추가)

프로젝트 루트에 `.env` 파일 생성:
```env
DISCORD_TOKEN=your_bot_token_here
```

실행:
```bash
python main.py
```

## 필요 권한
- 음성 채널 연결/말하기
- 메시지/임베드 전송
- 애플리케이션 명령 사용

## 디렉터리 구조
```
sicksick/
    main.py
    commands/
        play.py
        pause.py
        stop.py
        skip.py
        queue.py
        nowplaying.py
        volume.py
        karaoke.py
    utils/
        logging.py
        constants.py
        extension_loader.py
        data_manager.py
        data_health_checker.py
        graceful_shutdown.py
        lyrics_sync.py
    data/
    requirements.txt
    README.md
    .env
```

## 싱크가사(LRC) 안내
- 곡명/URL로 LRC 파일 자동 검색 및 실시간 표시
- LRC가 없으면 일반 가사 안내 또는 미지원 메시지 출력

## 노래방 채점 안내
- MR(반주) 버전으로 재생, 원곡(보컬 포함)과 유저 음성 비교
- 피치/에너지/발음/길이 등 종합 점수 제공

## 종료 처리
SIGINT/SIGTERM 발생 시 `utils.graceful_shutdown`에서 데이터 저장 콜백 실행

## 라이선스
개인/비상업적 용도 사용 가능. 문의: stack1245
    data/
```

## 종료 처리

`utils.graceful_shutdown`에서 SIGINT/SIGTERM 감지 후 등록된 콜백(데이터 저장) 실행.

## 라이선스

프로젝트 내 별도 명시 없으면 개인 용도 사용 가능. 필요 시 문의.
