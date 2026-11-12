# Live Subtitles for macOS: setup guide

Offline, real-time English subtitles for anything your Mac plays (YouTube, movies, Zoom, games), shown in a transparent floating bar that stays on top of every app.

Files in this folder:

| File | What it is |
|---|---|
| `live_subtitles.py` | The app (one file, fully commented) |
| `requirements.txt` | Python packages |
| `config.example.json` | Example settings file |
| `SETUP_GUIDE.md` | This guide |

Total time: about 20 minutes. Works on Apple Silicon and Intel Macs, macOS 12 or newer.

---

## 0. Why BlackHole is needed

macOS does not let apps record what comes out of the speakers. BlackHole is a free virtual audio device that acts as a loopback: whatever is sent to it can be recorded as if it were a microphone. We create a **Multi-Output Device** so that sound goes to your speakers/headphones *and* to BlackHole at the same time. The app then records BlackHole.

```
Any app ──► Multi-Output Device ──► MacBook speakers / AirPods (you hear it)
                                └─► BlackHole 2ch ──► live_subtitles.py
```

---

## 1. Install Homebrew (skip if `brew --version` already works)

Open **Terminal** and run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### In mainland China: use a Homebrew mirror

If the command above hangs or `brew install` is very slow, use the Tsinghua (TUNA) mirror. Add these lines to `~/.zshrc`, then run `source ~/.zshrc`:

```bash
export HOMEBREW_API_DOMAIN="https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles/api"
export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles"
export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/brew.git"
export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/homebrew-core.git"
export HOMEBREW_PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
```

If installing Homebrew itself fails, install it via the mirror:

```bash
git clone --depth=1 https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/install.git brew-install
/bin/bash brew-install/install.sh
rm -rf brew-install
```

(USTC works too: replace `mirrors.tuna.tsinghua.edu.cn` with `mirrors.ustc.edu.cn` and follow their Homebrew help page.)

On Apple Silicon, after installing, make sure brew is on your PATH:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

---

## 2. Install BlackHole, PortAudio and Python

```bash
brew install --cask blackhole-2ch
brew install portaudio python@3.12
```

- macOS will ask for your password to install the BlackHole driver.
- **Restart your Mac afterwards** (or run `sudo killall coreaudiod`), otherwise BlackHole may not appear.
- In China, the BlackHole cask downloads from GitHub and may time out even with the mirror (casks are not mirrored). If so, download the installer `.pkg` for **BlackHole 2ch** from https://existential.audio/blackhole/ (or the GitHub releases page of ExistentialAudio/BlackHole) in your browser, double-click it, and continue.

Check it worked: open **Audio MIDI Setup** (Spotlight: Cmd+Space, type "Audio MIDI"). You should see **BlackHole 2ch** in the left list.

---

## 3. Create the Multi-Output Device

1. Open **Audio MIDI Setup** (`/Applications/Utilities/Audio MIDI Setup.app`).
2. Click the **+** button at the bottom left and choose **Create Multi-Output Device**.
3. In the right pane, tick:
   - your real output first: **MacBook Pro Speakers**, **External Headphones**, or your **AirPods**
   - **BlackHole 2ch**
4. Set **Primary Device** (sometimes called Clock Source) to your real speakers/headphones.
5. Tick **Drift Correction** for **BlackHole 2ch** (not for the primary device).
6. Optional: double-click the name and rename it to `Speakers + BlackHole`.
7. Make sure both devices use the **same sample rate** (48,000 Hz is a good choice). Select each device in the left list and check the **Format** dropdown.

### Send all system sound to it

**System Settings → Sound → Output → choose the Multi-Output Device** (`Speakers + BlackHole`).

Or hold **Option** and click the volume icon in the menu bar, and choose it there.

> **Volume keys stop working** with a Multi-Output Device. That's a macOS limitation. Set the volume of your speakers in Audio MIDI Setup (select the speaker device → Output → Master slider), or control volume inside the player (YouTube, IINA, VLC...). When you are done with subtitles, switch the output back to your normal speakers to get volume keys back.
>
> **Using AirPods / Bluetooth?** Create a separate Multi-Output Device with the AirPods ticked (and AirPods as the Primary Device), because a Multi-Output Device only plays to the outputs ticked in it.

### Do NOT change the input

Leave **System Settings → Sound → Input** on your microphone. The app picks BlackHole by name, so the system input doesn't matter.

---

## 4. Install the Python packages

Put the files from this folder in e.g. `~/live-subtitles`, then:

```bash
cd ~/live-subtitles
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

In China, use the Tsinghua PyPI mirror:

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# or make it permanent:
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

Next time you open a new Terminal, run `cd ~/live-subtitles && source .venv/bin/activate` first.

---

## 5. Download the Whisper model (once)

The app downloads the model automatically from Hugging Face the first time it runs and then works fully offline. Sizes (English-only `.en` versions are used):

| `--model` | Download | Speed on M1/M2 | Accuracy | Use for |
|---|---|---|---|---|
| `tiny`  | ~75 MB  | fastest | OK | older Intel Macs, lowest latency |
| `base`  | ~145 MB | fast | good | **default, best balance** |
| `small` | ~485 MB | slower (≈1 s per chunk) | very good | M1 Pro/M2/M3 and newer |

### In mainland China: Hugging Face is usually blocked

**Option A: use the hf-mirror.com mirror (easiest).** Run this in the same Terminal before the app:

```bash
export HF_ENDPOINT=https://hf-mirror.com
python live_subtitles.py --model base
```

Add `export HF_ENDPOINT=https://hf-mirror.com` to `~/.zshrc` to make it permanent.

**Option B: download the model folder yourself and point the app at it.**

```bash
export HF_ENDPOINT=https://hf-mirror.com
pip install -U huggingface_hub
hf download Systran/faster-whisper-base.en --local-dir ~/whisper-models/base.en
#   (older huggingface_hub: huggingface-cli download Systran/faster-whisper-base.en --local-dir ~/whisper-models/base.en)

python live_subtitles.py --model ~/whisper-models/base.en
```

Repos: `Systran/faster-whisper-tiny.en`, `Systran/faster-whisper-base.en`, `Systran/faster-whisper-small.en`. You can also download the files (`config.json`, `model.bin`, `tokenizer.json`, `vocabulary.txt`) from https://hf-mirror.com/Systran/faster-whisper-base.en/tree/main in a browser into one folder.

**The VAD filter needs no download.** The Silero VAD model ships inside the `faster-whisper` package.

After the first successful run you can force fully-offline mode with `export HF_HUB_OFFLINE=1`.

---

## 6. Allow microphone access for Terminal

macOS treats BlackHole as a microphone, so the app that runs Python needs permission.

**System Settings → Privacy & Security → Microphone →** turn on **Terminal** (or iTerm / VS Code / whatever you run Python from). If it's not listed, run step 7's `--test-audio` once; macOS will ask. **Quit and reopen Terminal after changing it.**

For the **global hotkeys** (Ctrl+Option+Q/P/H), also enable your terminal app in **System Settings → Privacy & Security → Input Monitoring**, then restart the terminal.

---

## 7. Test, then run

```bash
python live_subtitles.py --list-devices   # BlackHole 2ch should be listed as an input
python live_subtitles.py --test-audio     # play a YouTube video: the bar must move
python live_subtitles.py                  # start the overlay (base model)
```

Examples:

```bash
python live_subtitles.py --model tiny --font-size 24
python live_subtitles.py --model small --text-color yellow --bg-opacity 0.3
python live_subtitles.py --bg-opacity 0 --text-color "#FFFFFF"   # text only, with shadow
python live_subtitles.py --config config.example.json            # settings from a file
python live_subtitles.py --help                                   # every option
```

### Settings you can change

| Option | Default | Meaning |
|---|---|---|
| `--model` | `base` | `tiny` / `base` / `small` (or `medium`, or a local folder) |
| `--font-size` | `28` | subtitle size in points |
| `--text-color` | `#FFFFFF` | any name (`yellow`) or hex (`#FFD700`) |
| `--bg-color` | `#000000` | background box color |
| `--bg-opacity` | `0.55` | 0 = invisible box, 1 = solid |
| `--width` | `0.70` | overlay width as a fraction of the screen |
| `--max-lines` | `2` | recent lines kept on screen |
| `--clear-after` | `5` | seconds of quiet before the subtitle disappears |
| `--min-chunk` / `--max-chunk` | `1.0` / `4.0` | chunk length in seconds; lower `--max-chunk` = lower latency but more broken sentences |
| `--partial-interval` | `0.6` | show words while the sentence is still being spoken, every N seconds (0 = off) |
| `--silence-rms` | `0.004` | loudness below which audio counts as silence |
| `--click-through` | off | clicks pass through the overlay (control it with global hotkeys) |
| `--device` | `BlackHole` | capture device name or index |

The same keys (with underscores, like `font_size`) can go in a JSON file passed with `--config`.

### Using the overlay

- **Drag** the subtitle box to move it.
- It shows on every desktop/Space and on top of full-screen videos (needs the `pyobjc` packages from requirements.txt).
- Nothing is drawn when nobody is talking. Silent and empty chunks, `[Music]`-style tags and typical Whisper "Thanks for watching" hallucinations are dropped.

### Keyboard shortcuts

| Keys | Where | Action |
|---|---|---|
| **Ctrl+Option+Q** | anywhere | quit cleanly |
| **Ctrl+Option+P** | anywhere | pause / resume transcription |
| **Ctrl+Option+H** | anywhere | hide / show the overlay |
| **Esc** or **Cmd+Q** | overlay focused (click it once) | quit cleanly |
| **Cmd+P** | overlay focused | pause / resume |
| **Ctrl+C** | in Terminal | quit cleanly |

"Cleanly" means: the audio stream is closed, the transcription thread stops, and the transcript/OBS files are flushed and closed.

---

## 8. Troubleshooting audio capture

| Symptom | Fix |
|---|---|
| `No input device containing "BlackHole"` | BlackHole isn't loaded. Restart the Mac, or `sudo killall coreaudiod`. Check it appears in Audio MIDI Setup. Re-install with `brew reinstall --cask blackhole-2ch`. |
| `--test-audio` bar stays at **0.0000** | 1) System output isn't the Multi-Output Device (step 3). 2) **BlackHole isn't ticked** in the Multi-Output Device. 3) **Terminal has no Microphone permission** (step 6): macOS then silently delivers zeros. Quit & reopen Terminal after granting. 4) The video is muted in the player. |
| You hear nothing anymore | You chose BlackHole alone as output. Choose the Multi-Output Device, and make sure your speakers are ticked in it. |
| Volume keys don't work | Normal with Multi-Output; see the note in step 3. |
| Crackling / `input overflow` messages | Set both devices in the Multi-Output Device to the same sample rate (48 kHz), and enable Drift Correction on BlackHole. Use a smaller model. |
| `PortAudio library not found` / `OSError` | `brew install portaudio`, then `pip install --force-reinstall sounddevice`. |
| `Error opening InputStream: Invalid sample rate` (`-9997`) | In Audio MIDI Setup set BlackHole 2ch to 48,000 Hz (or 44,100), then rerun. The app always uses the device's own rate. |
| `Error -9986` / `Internal PortAudio error` after sleep or plugging headphones | CoreAudio changed devices under the app. Quit and restart the app; if it persists, `sudo killall coreaudiod`. |
| Subtitles lag further and further behind | The model is too slow for your Mac. Use `--model tiny` or `base`, or `--max-chunk 3`. The app drops backlog automatically and prints `[lag]` when it does. |
| Model download fails / hangs (China) | Use `HF_ENDPOINT=https://hf-mirror.com` or a local model folder (step 5). |
| `zsh: illegal hardware instruction` on Apple Silicon | You're running an Intel (x86) Python under Rosetta. Use Homebrew's `/opt/homebrew/bin/python3.12` and recreate the venv. |
| Overlay hidden behind full-screen video | Install `pyobjc-framework-Cocoa` (in requirements.txt) and restart the app. |
| Global hotkeys don't work | Grant **Input Monitoring** to your terminal app (step 6), restart the terminal. The overlay's own Esc/Space shortcuts work without it. |
| Too many fragments / words cut mid-sentence | Raise `--max-chunk` to 5–6 (more latency, more complete sentences). |
| Music or noise produces junk text | Raise `--silence-rms` (e.g. 0.01), or use a larger model. |

---

## 9. Optional extras

All three are built into `live_subtitles.py`; switch them on with flags.

### a) Subtitles in a text file for OBS

```bash
python live_subtitles.py --obs-file ~/live-subtitles/obs_subtitles.txt
```

The file always contains the lines currently on screen and is emptied when the overlay clears. Writes are atomic, so OBS never reads half a line.

In OBS: **Sources → + → Text (FreeType 2)** → tick **Read from file** → choose `obs_subtitles.txt`. Style it with OBS's own font and outline settings. Tip: add `--bg-opacity 0` or `--click-through` if you also keep the overlay on screen while streaming.

### b) Hotkey to pause transcription

Already included: **Ctrl+Option+P** anywhere (or **Cmd+P** on the focused overlay). While paused the overlay shows "⏸ Paused", incoming audio is discarded (no catch-up burst when you resume), and nothing is written to the files.

### c) Save the full transcript

```bash
python live_subtitles.py --transcript                    # creates transcript_YYYYMMDD_HHMMSS.txt
python live_subtitles.py --transcript ~/Documents/lecture.txt   # append to a file you choose
```

Each line is timestamped:

```
# Live transcript started 2026-11-12 14:03:10
[14:03:15] Hello everyone, welcome back to the channel.
[14:03:19] Today we are going to talk about live subtitles on the Mac.
# Ended 2026-11-12 14:40:02
```

All together:

```bash
python live_subtitles.py --model small --obs-file obs_subtitles.txt --transcript
```

---

## 10. Chinese (or other languages) into English subtitles

Whisper can translate speech straight into English, still fully offline. Use the multilingual model (the app picks it automatically when you add `--translate`). `small` is the smallest size that translates Chinese well. `base` works but makes more mistakes.

```bash
# Chinese video -> English subtitles
python live_subtitles.py --translate --language zh --model small

# Mixed or unknown language: detect it automatically
python live_subtitles.py --translate --model small

# Show Chinese subtitles (no translation)
python live_subtitles.py --language zh --model small
```

The first run downloads the multilingual model (`Systran/faster-whisper-small`, about 480 MB). In China, run `export HF_ENDPOINT=https://hf-mirror.com` first. Translation is a bit slower than English-only mode (roughly 0.5 to 1.5 s per line on an M1). If it lags, use `--model base` or `--partial-interval 1.0`.

---

## 11. How the latency works (for tuning)

1. Audio arrives in 100 ms blocks, gets mixed to mono and resampled to 16 kHz.
2. Blocks are buffered. As soon as there is at least `--min-chunk` seconds **and** the last `--pause-len` seconds are quiet (someone paused), the buffer is sent to Whisper. If nobody pauses, it is cut at `--max-chunk` seconds.
3. Chunks that are entirely below `--silence-rms` are skipped without running the model.
4. faster-whisper runs with `vad_filter=True` (Silero VAD) to remove non-speech, `language="en"`, greedy decoding (`beam_size=1`) and `condition_on_previous_text=False` to avoid repetition loops.
5. Empty, punctuation-only, repeated and typical hallucinated outputs are dropped.

Typical delay from speech to subtitle: about 1.5–4.5 s with `base` on an M1, depending on how often the speaker pauses.
