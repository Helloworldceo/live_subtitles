# Live Subtitles for macOS (실시간 자막)

[English](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · **한국어**

Mac에서 **재생되는 모든 소리**(YouTube, 영화, Zoom, 게임 등)에 실시간으로 자막을 띄웁니다. 자막은 투명한 바에 표시되고, 전체 화면 Chrome을 포함한 모든 앱 위에 항상 떠 있습니다.

- **완전 오프라인**: 음성 인식은 [faster-whisper](https://github.com/SYSTRAN/faster-whisper)로 Mac에서 직접 처리합니다. 클라우드를 쓰지 않습니다.
- **마이크가 아니라 시스템 소리를 녹음**: 무료 드라이버 [BlackHole](https://github.com/ExistentialAudio/BlackHole)로 스피커 출력을 녹음합니다.
- **영어 자막**을 보여 주고, **한국어·중국어 등 약 95개 언어는 영어로 번역**해서 보여 줍니다.
- **낮은 지연**: 말하는 도중에도 글자가 나타납니다.

---

## 받기와 설치 (단계별)

필요 조건: macOS 12 이상(Apple Silicon 또는 Intel), 여유 공간 약 1.5GB

### 1단계: 프로젝트 내려받기

**터미널**을 열고 다음을 실행하세요.

```bash
git clone https://github.com/Helloworldceo/live_subtitles.git
cd live_subtitles
```

git이 없다면 GitHub에서 **Code → Download ZIP**으로 내려받아 압축을 풀고, `cd`로 그 폴더에 들어가세요.

### 2단계: 설치 프로그램 실행

```bash
./install.sh                 # 일반 설치
./install.sh --translate     # 영어 번역용 다국어 모델도 함께 설치
```

설치 프로그램이 하는 일:
1. Homebrew가 없으면 설치합니다.
2. `portaudio`, `python@3.12`, **BlackHole 2ch** 드라이버를 설치합니다. 도중에 Mac 암호를 한 번 묻습니다.
3. `.venv`에 Python 환경을 만들고 `requirements.txt`의 패키지를 모두 설치합니다.
4. Whisper 모델을 한 번 내려받습니다. 이후에는 오프라인으로 작동합니다.

### 3단계: Mac 재시동

BlackHole은 재시동해야 나타납니다.

### 4단계: 시스템 소리를 BlackHole로도 보내기

1. **Audio MIDI 설정**을 엽니다. (Cmd+Space를 누르고 "Audio MIDI" 입력)
2. 왼쪽 아래 **+**를 누르고 **다중 출력 기기 생성**을 선택합니다.
3. **스피커(또는 헤드폰)**와 **BlackHole 2ch**에 모두 체크합니다.
4. **주 기기**를 스피커로 지정합니다. **드리프트 보정**은 BlackHole에만 켜고, 두 기기 모두 **48,000Hz**로 설정합니다.
5. **시스템 설정 → 사운드 → 출력**에서 방금 만든 **다중 출력 기기**를 선택합니다.

> 다중 출력 기기를 쓰는 동안에는 키보드 음량 키가 작동하지 않습니다. macOS의 제한이니 음량은 플레이어에서 조절하세요.

### 5단계: 터미널에 권한 주기

**시스템 설정 → 개인정보 보호 및 보안**에서:
- **마이크**: **터미널**을 켭니다. 이 권한이 없으면 무음만 녹음됩니다.
- **입력 모니터링**: **터미널**을 켭니다. 선택 사항이며, Ctrl+Option 단축키를 쓸 때만 필요합니다.

설정한 뒤 터미널을 종료하고 다시 여세요.

### 6단계: 테스트 후 실행

```bash
./run.sh --list-devices     # 입력 장치에 "BlackHole 2ch"가 보여야 합니다
./run.sh --test-audio       # 동영상을 재생하면 레벨 막대가 움직여야 합니다
./run.sh                    # 자막 시작
```

---

## 사용법

| 하고 싶은 것 | 명령 |
|---|---|
| 영어 자막 | `./run.sh` |
| **한국어 영상 → 영어 자막** | `./run.sh --translate --language ko --model small` |
| 어떤 언어든 영어로 (자동 감지) | `./run.sh --translate --model small` |
| 한국어 자막 (번역 없이) | `./run.sh --language ko --model small` |
| 모든 옵션 보기 | `./run.sh --help` |

## 단축키

| 키 | 동작 |
|---|---|
| **Ctrl+Option+Q** | 종료 |
| **Ctrl+Option+P** | 일시정지 / 다시 시작 |
| **Ctrl+Option+H** | 자막 바 숨기기 / 보이기 |
| **Ctrl+C** (터미널에서) | 종료 |

## 자주 생기는 문제

| 증상 | 해결 |
|---|---|
| BlackHole이 안 보임 | Mac을 재시동하거나 `sudo killall coreaudiod`를 실행하세요. |
| `--test-audio`가 계속 0 | 출력이 다중 출력 기기가 아니거나, 다중 출력 기기에서 BlackHole이 체크되지 않았거나, 터미널에 마이크 권한이 없습니다. |
| 소리가 안 남 | BlackHole만 고르지 말고 다중 출력 기기를 선택하세요. |
| 자막이 늦게 나옴 | 더 작은 `--model`을 쓰거나 `--cpu-threads 8`을 추가하세요. |

자세한 안내(영어)는 [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)에 있습니다.
