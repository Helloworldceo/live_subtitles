# Live Subtitles for macOS

**English** · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

Real-time subtitles for **anything playing on your Mac**: YouTube, movies, Zoom, games. They appear in a transparent bar that floats on top of every app, including full-screen Chrome.

- **100% offline.** Speech recognition runs locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper). No cloud APIs and no account.
- **System audio, not just the mic.** It records what your speakers play, through the free [BlackHole](https://github.com/ExistentialAudio/BlackHole) loopback driver.
- **English subtitles**, or **Chinese (and ~95 other languages) translated into English**.
- **Low latency.** Words appear while they are being spoken, refreshed every 0.6 s.
- **Configurable** model size, font, colors, background opacity, position.
- **Extras:** a live text file for OBS, a full timestamped transcript, and global hotkeys.

---

## How it works

```
Any app ──► Multi-Output Device ──► your speakers / headphones   (you hear it)
                               └──► BlackHole 2ch (virtual cable)
                                          │
                     live_subtitles.py records BlackHole like a microphone
                                          │
          100 ms blocks → mono 16 kHz → cut at natural pauses (max 4 s)
          silent chunks skipped → Silero VAD → faster-whisper (local)
                                          │
              always-on-top transparent subtitle bar  (+ OBS file, transcript)
```

1. macOS can't record its own speaker output, so **BlackHole** acts as a virtual audio cable.
2. A **Multi-Output Device** sends sound to your speakers *and* to BlackHole at the same time.
3. The app records BlackHole, splits the audio into short chunks at natural pauses, and throws away silence.
4. **faster-whisper** turns each chunk into text on your CPU. While a sentence is still being spoken, it shows a live preview that gets replaced by the final line.
5. The text is drawn in a floating bar that joins every desktop Space and stays above full-screen apps.

---

## Install (step by step)

Requirements: macOS 12 or newer, on Apple Silicon or Intel, with about 1.5 GB of free disk space.

### Step 1: Download this repository

```bash
git clone https://github.com/Helloworldceo/live_subtitles.git
cd live_subtitles
```

(No git? Click **Code → Download ZIP** on GitHub, unzip it, and `cd` into the folder.)

### Step 2: Run the installer

```bash
./install.sh
```

**In mainland China**, use the mirrors (Tsinghua for Homebrew and PyPI, hf-mirror.com for the models):

```bash
./install.sh --china
```

Add `--translate` to also download the multilingual model for Chinese → English:

```bash
./install.sh --china --translate
```

The installer:
1. installs Homebrew if it's missing;
2. installs `portaudio`, `python@3.12` and the **BlackHole 2ch** driver (macOS asks for your password once);
3. creates a private Python environment in `.venv` and installs everything in `requirements.txt`;
4. downloads the Whisper model(s) once, after which everything works offline.

### Step 3: Restart your Mac

BlackHole only appears after a restart.

### Step 4: Route system audio through BlackHole

1. Open **Audio MIDI Setup** (Cmd+Space, then type "Audio MIDI").
2. Click **+** at the bottom left and choose **Create Multi-Output Device**.
3. Tick your **speakers or headphones** and **BlackHole 2ch**.
4. Set **Primary Device** to your speakers. Tick **Drift Correction** for BlackHole only. Set both devices to **48,000 Hz**.
5. Open **System Settings → Sound → Output** and select the **Multi-Output Device**.

> Volume keys don't work while a Multi-Output Device is selected, which is a macOS limitation. Use the player's volume instead, or switch the output back to your speakers when you're done.

### Step 5: Give Terminal permission

**System Settings → Privacy & Security**:
- **Microphone:** turn on **Terminal**. macOS treats BlackHole as a microphone, and without this you only get silence.
- **Input Monitoring:** turn on **Terminal**. This is optional and only needed for the global Ctrl+Option hotkeys.

Quit and reopen Terminal afterwards.

### Step 6: Test, then run

```bash
./run.sh --list-devices     # "BlackHole 2ch" should be listed as an input
./run.sh --test-audio       # play a video: the level bar must move
./run.sh                    # start the subtitles
```

---

## Usage

| What you want | Command |
|---|---|
| English subtitles (default `base` model) | `./run.sh` |
| More accurate English | `./run.sh --model small` |
| Fastest (older Macs) | `./run.sh --model tiny` |
| Chinese video → English subtitles | `./run.sh --translate --language zh --model small --cpu-threads 8` |
| Any language → English (auto-detect) | `./run.sh --translate --model small` |
| Japanese, Korean, Spanish … → English | `./run.sh --translate --language ja --model small` (see [Other languages](#other-languages)) |
| Chinese subtitles (no translation) | `./run.sh --language zh --model small` |
| Big yellow text, see-through box | `./run.sh --font-size 34 --text-color yellow --bg-opacity 0.3` |
| Settings from a file | `./run.sh --config config.example.json` |
| Every option | `./run.sh --help` |

### Other spoken languages

Whisper understands about 99 languages. Pass the language code with `--language`, and add `--translate` if you want English subtitles instead of subtitles in the original language. Translation needs the multilingual model, so install with `./install.sh --translate` or let the first run download it.

| Language | Code | Translate to English | Subtitles in that language |
|---|---|---|---|
| Chinese | `zh` | `./run.sh --translate --language zh --model small` | `./run.sh --language zh --model small` |
| Spanish | `es` | `./run.sh --translate --language es --model medium` | `./run.sh --language es --model small` |
| French | `fr` | `./run.sh --translate --language fr --model medium` | `./run.sh --language fr --model small` |
| Japanese | `ja` | `./run.sh --translate --language ja --model small` | `./run.sh --language ja --model small` |
| Korean | `ko` | `./run.sh --translate --language ko --model small` | `./run.sh --language ko --model small` |
| German | `de` | `./run.sh --translate --language de --model medium` | `./run.sh --language de --model small` |
| Unknown or mixed | `auto` | `./run.sh --translate --model small` | `./run.sh --language auto --model small` |

Other codes follow the same pattern, for example `ru`, `pt`, `it`, `ar`, `hi`, `vi`, `th` or `id`. Setting the language explicitly is about twice as fast as `auto`. For better accuracy use `--model medium`, which is slower. European languages translate noticeably better with `medium` than with `small`.

How to download the models, the full list of language codes, and tested results: see **[Other languages: models and codes](#other-languages-models-and-codes)** below.

### Keyboard shortcuts

| Keys | Works | Action |
|---|---|---|
| **Ctrl+Option+Q** | anywhere | quit cleanly |
| **Ctrl+Option+P** | anywhere | pause / resume subtitles |
| **Ctrl+Option+H** | anywhere | hide / show the bar |
| **Esc** or **Cmd+Q** | bar focused | quit |
| **Cmd+P** | bar focused | pause / resume |
| **Ctrl+C** | in Terminal | quit |

Drag the bar to move it. It also follows your mouse to another display.

### Extras

```bash
./run.sh --obs-file obs_subtitles.txt   # OBS: Text (FreeType 2) → "Read from file"
./run.sh --transcript                   # saves transcript_YYYYMMDD_HHMMSS.txt
./run.sh --transcript ~/Documents/lecture.txt
```

### Main settings

| Option | Default | Meaning |
|---|---|---|
| `--model` | `base` | `tiny` / `base` / `small` / `medium`, or a local model folder |
| `--translate` | off | translate speech into English (multilingual model) |
| `--language` | `en` | spoken language: `en`, `zh`, `ja` … or `auto` |
| `--font-size` | `28` | text size |
| `--text-color` | `#FFFFFF` | color name or hex |
| `--bg-opacity` | `0.55` | 0 = invisible box, 1 = solid |
| `--max-lines` | `2` | lines kept on screen |
| `--partial-interval` | `0.6` | seconds between live preview updates (0 = off) |
| `--min-speech` | `0.3` | seconds of detected speech needed before anything is shown (raise it if noise still produces text) |
| `--max-chunk` | `4.0` | longest chunk before a forced cut |
| `--device` | `BlackHole` | capture device name or index |

---

## Other languages: models and codes

Whisper understands about 99 languages. You can use them in two ways:

- **Translate to English subtitles**: `--translate --language <code>`
- **Subtitles in the spoken language** (Chinese subtitles for Chinese speech, and so on): `--language <code>`, without `--translate`

Whisper can only translate *into English*. Subtitles in other target languages (for example English → Chinese) are not supported.

### Step 1: Get a multilingual model (one time)

The default `base.en` model is English-only. Other languages need a multilingual model:

```bash
./install.sh --translate                  # downloads "small" (~480 MB): good for Chinese, Japanese, Korean
./install.sh --model medium               # downloads "medium" (~1.5 GB): better translation, slower
./install.sh --china --model medium       # same, through the mainland-China mirrors
```

Already installed? Running `install.sh` again is safe. It keeps your `.venv` and only downloads what's missing. Add `--no-blackhole` to skip the driver step.

<details>
<summary>Download a model by hand instead</summary>

```bash
.venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8')"
# mainland China: put  HF_ENDPOINT=https://hf-mirror.com  in front
```
Model folders are also on Hugging Face (`Systran/faster-whisper-small`, `Systran/faster-whisper-medium`, `Systran/faster-whisper-large-v3`). Download one into a folder and run with `--model /path/to/folder`.
</details>

| Model | Download | Speed per line (M-series) | Use for |
|---|---|---|---|
| `small` | ~480 MB | ~1 s | Chinese, Japanese, Korean → English; subtitles in the spoken language |
| `medium` | ~1.5 GB | ~2–3 s | better translation, especially European languages (Spanish, French, German ...) |
| `large-v3` | ~3 GB | too slow for live use on most Macs | best quality, for recorded videos / transcripts |

### Step 2: Run with the language code

Use the commands in the [Other spoken languages](#other-spoken-languages) table above, with any code from this list:

| Language | Code | | Language | Code | | Language | Code |
|---|---|---|---|---|---|---|---|
| Chinese (Mandarin) | `zh` | | French | `fr` | | Arabic | `ar` |
| Japanese | `ja` | | German | `de` | | Hindi | `hi` |
| Korean | `ko` | | Spanish | `es` | | Turkish | `tr` |
| Vietnamese | `vi` | | Portuguese | `pt` | | Russian | `ru` |
| Thai | `th` | | Italian | `it` | | Persian | `fa` |
| Indonesian | `id` | | Dutch | `nl` | | Amharic | `am` |

The full list of codes is in [Whisper's tokenizer](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py) (`LANGUAGES`).

**Tips**

- **Always give `--language`** when you know it. Auto-detect costs about 1 s per line and can guess wrong on short clips.
- Quality depends on the language. Widely spoken languages work best; low-resource languages (for example Amharic) may be poor even with `medium`.
- If a translation comes out in the original language or garbled, use a bigger model (`--model medium`).
- Chinese, Japanese and Korean characters display correctly in the overlay; macOS picks a suitable font automatically.

Tested on a MacBook (Apple Silicon) with `small` and `--cpu-threads 8`:

| Spoken | Subtitles in the spoken language | Translated to English |
|---|---|---|
| Chinese | 今天我们来做一个非常好吃的汉堡,首先把牛肉切碎… (1.1 s) | "Today we are going to make a very delicious burger. First chop the beef…" (1.0 s) |
| Japanese | 今日は、とても美味しいハンバーガーを作ります (0.9 s) | "Today, I will make a very delicious hamburger." (0.9 s) |
| Spanish | "Hoy vamos a preparar una hamburguesa muy deliciosa." (0.9 s) | weak with `small`: use `--model medium` |

---

## Speed (MacBook, Apple Silicon, CPU only)

| Mode | Time per subtitle line |
|---|---|
| English, `base` | ~0.3–0.4 s |
| Chinese → English, `small`, `--language zh --cpu-threads 8` | ~0.7–0.8 s |
| Auto-detect → English, `small` | ~2 s |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `No input device containing "BlackHole"` | Restart the Mac, or run `sudo killall coreaudiod`. |
| `--test-audio` stays at 0 | Output isn't set to the Multi-Output Device, BlackHole isn't ticked in it, or Terminal has no Microphone permission. |
| No sound from the speakers | Pick the Multi-Output Device, not BlackHole alone. |
| Model download hangs (China) | `export HF_ENDPOINT=https://hf-mirror.com`, or re-run `./install.sh --china`. |
| Subtitles lag | Use a smaller `--model`, or add `--cpu-threads 8`. |
| Hotkeys don't work | Give Terminal **Input Monitoring** permission and restart Terminal. |

The full guide, with manual steps, mirrors and more fixes, is in **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)**.

---

## Files

| File | Purpose |
|---|---|
| `live_subtitles.py` | the app (single file, commented) |
| `install.sh` | one-command installer |
| `run.sh` | starts the app with the project's `.venv` |
| `requirements.txt` | Python packages |
| `config.example.json` | example settings file |
| `docs/SETUP_GUIDE.md` | detailed manual setup and troubleshooting |
| `README.*.md` | install guides in Chinese, Spanish, French, Japanese, Korean |
