#!/usr/bin/env bash
# install.sh - one-command installer for Live Subtitles on macOS.
#
#   ./install.sh                # normal install
#   ./install.sh --china        # use Tsinghua (Homebrew, PyPI) + hf-mirror.com (models)
#   ./install.sh --translate    # also download the multilingual model for Chinese -> English
#   ./install.sh --no-blackhole # skip the BlackHole driver (already installed)
#   ./install.sh --model medium # also download another model (repeatable): tiny, base, small,
#                               # medium, large-v3 (multilingual) or tiny.en/base.en/small.en ...
#
# What it does:
#   1. installs Homebrew if missing
#   2. brew install portaudio python@3.12, and the BlackHole 2ch audio driver
#   3. creates .venv and installs requirements.txt
#   4. downloads the Whisper model(s) so the app works offline
#   5. prints the manual steps that macOS does not allow scripts to do
set -euo pipefail

CHINA=0
TRANSLATE=0
BLACKHOLE=1
EXTRA_MODELS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --china) CHINA=1 ;;
    --translate) TRANSLATE=1 ;;
    --no-blackhole) BLACKHOLE=0 ;;
    --model)
      [[ $# -ge 2 ]] || { echo "--model needs a name, e.g. --model medium"; exit 1; }
      EXTRA_MODELS+=("$2"); shift ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1 (see --help)"; exit 1 ;;
  esac
  shift
done

cd "$(dirname "$0")"
step() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m%s\033[0m\n' "$*"; }

if [[ "$(uname)" != "Darwin" ]]; then
  echo "This installer is for macOS only."; exit 1
fi

PIP_ARGS=()
if [[ $CHINA -eq 1 ]]; then
  step "Using China mirrors (Tsinghua for Homebrew/PyPI, hf-mirror.com for models)"
  export HOMEBREW_API_DOMAIN="https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles/api"
  export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles"
  export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/brew.git"
  export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/homebrew-core.git"
  export HOMEBREW_PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
  export HF_ENDPOINT="https://hf-mirror.com"
  PIP_ARGS=(-i "https://pypi.tuna.tsinghua.edu.cn/simple")
fi

# ---------------------------------------------------------------- 1. Homebrew
step "1/5 Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [[ -x "$b" ]] && eval "$("$b" shellenv)" && break
  done
fi
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not found, installing it (you may be asked for your password) ..."
  if [[ $CHINA -eq 1 ]]; then
    tmp="$(mktemp -d)"
    git clone --depth=1 https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/install.git "$tmp/brew-install"
    /bin/bash "$tmp/brew-install/install.sh"
  else
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [[ -x "$b" ]] && eval "$("$b" shellenv)" && break
  done
fi
brew --version | head -1

# ---------------------------------------------------------------- 2. packages
step "2/5 PortAudio, Python 3.12 and BlackHole"
brew install portaudio python@3.12
NEED_RESTART=0
if [[ $BLACKHOLE -eq 1 ]]; then
  if brew list --cask blackhole-2ch >/dev/null 2>&1 || [[ -d "/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver" ]]; then
    echo "BlackHole 2ch is already installed."
  else
    echo "Installing the BlackHole 2ch audio driver. macOS will ask for your password."
    if brew install --cask blackhole-2ch; then
      NEED_RESTART=1
    else
      warn "BlackHole install failed. Download the BlackHole 2ch .pkg from https://existential.audio/blackhole/ and install it by hand."
    fi
  fi
fi

# ---------------------------------------------------------------- 3. venv
step "3/5 Python environment (.venv)"
PY="$(brew --prefix python@3.12)/bin/python3.12"
[[ -x "$PY" ]] || PY="$(command -v python3.12 || command -v python3)"
if [[ ! -d .venv ]]; then
  "$PY" -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip ${PIP_ARGS[@]+"${PIP_ARGS[@]}"}
.venv/bin/python -m pip install -r requirements.txt ${PIP_ARGS[@]+"${PIP_ARGS[@]}"}

# ---------------------------------------------------------------- 4. models
step "4/5 Whisper model(s) (one-time download, then fully offline)"
MODELS=("base.en")
[[ $TRANSLATE -eq 1 ]] && MODELS+=("small")
MODELS+=(${EXTRA_MODELS[@]+"${EXTRA_MODELS[@]}"})
for m in "${MODELS[@]}"; do
  echo "Downloading $m ..."
  .venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('$m', device='cpu', compute_type='int8'); print('  ok')" \
    || warn "Model $m failed to download. In China, rerun with --china (uses hf-mirror.com)."
done

# ---------------------------------------------------------------- 5. done
step "5/5 Done. A few steps macOS only lets you do by hand:"
cat <<EOF

  $( [[ $NEED_RESTART -eq 1 ]] && echo "0. RESTART your Mac now (BlackHole only appears after a restart)." )
  1. Open "Audio MIDI Setup" -> "+" -> "Create Multi-Output Device".
     Tick your speakers/headphones AND "BlackHole 2ch". Speakers = Primary Device,
     Drift Correction on BlackHole only, both at 48,000 Hz.
  2. System Settings -> Sound -> Output -> choose that Multi-Output Device.
  3. System Settings -> Privacy & Security -> Microphone: enable Terminal.
     (Optional, for Ctrl+Option hotkeys) Input Monitoring: enable Terminal.
     Quit and reopen Terminal afterwards.
  4. Test and run:
       ./run.sh --test-audio          # bar should move while a video plays
       ./run.sh                       # English subtitles
       ./run.sh --translate --language zh --model small   # Chinese -> English

  Full guide: docs/SETUP_GUIDE.md
EOF
