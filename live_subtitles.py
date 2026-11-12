#!/usr/bin/env python3
r"""
live_subtitles.py - Offline, real-time English subtitles for anything playing on your Mac.

How it works
------------
  macOS system audio --> Multi-Output Device --> (your speakers / headphones)
                                             \-> BlackHole 2ch (virtual loopback)
                                                      |
                     sounddevice (PortAudio) records BlackHole as an "input" device
                                                      |
            short chunks, cut at natural pauses  +  energy gate  +  Silero VAD filter
                                                      |
                       faster-whisper (English-only model, runs 100% locally)
                                                      |
              transparent, always-on-top, click-and-drag subtitle overlay (Qt)

Nothing is sent to the internet. The Whisper model is downloaded once (or copied in
manually) and then everything runs offline.

Quick start (after following SETUP_GUIDE.md):
    python live_subtitles.py --list-devices      # find BlackHole
    python live_subtitles.py --test-audio        # check that audio is actually arriving
    python live_subtitles.py --model base        # run the overlay
    python live_subtitles.py --translate --language zh --model small   # Chinese speech -> English

Keyboard shortcuts
------------------
  Global (work from any app; needs Input Monitoring permission, see the guide):
    Ctrl+Option+Q   quit cleanly
    Ctrl+Option+P   pause / resume transcription
    Ctrl+Option+H   hide / show the overlay
  When the overlay window is focused (click it once):
    Esc or Cmd+Q    quit cleanly
    Cmd+P           pause / resume
  In the terminal:
    Ctrl+C          quit cleanly

Optional extras (see --help):
    --obs-file subtitles.txt     keep the current subtitle in a text file for OBS
    --transcript                 save the full timestamped transcript to a file
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import queue
import re
import signal
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

try:
    import sounddevice as sd
except OSError as exc:  # PortAudio library missing
    sys.exit(
        f"Could not load PortAudio ({exc}).\n"
        "Fix: brew install portaudio && pip install --force-reinstall sounddevice"
    )

from PySide6.QtCore import QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)

WHISPER_SAMPLE_RATE = 16_000  # faster-whisper expects 16 kHz mono float32
LISTENING = "Listening ..."  # shown until the first subtitle arrives

# Friendly size names -> English-only Whisper checkpoints (".en" models are more
# accurate for English than the multilingual ones of the same size).
MODEL_ALIASES = {
    "tiny": "tiny.en",
    "base": "base.en",
    "small": "small.en",
    "medium": "medium.en",
}

# Phrases Whisper is known to "hallucinate" on music, noise or near-silence.
# They are only dropped when the chunk was quiet, so real speech is kept.
HALLUCINATIONS = {
    "you",
    "thank you",
    "thank you.",
    "thanks for watching",
    "thanks for watching!",
    "thank you for watching",
    "thank you for watching.",
    "please subscribe",
    "subscribe",
    "bye",
    "bye.",
    "so",
    "okay.",
    "i'm sorry",
    "i'm sorry. i'm sorry",
    "sorry",
    "oh",
    "hmm",
    "...",
}


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
@dataclass
class Config:
    # Audio
    device: str = "BlackHole"  # name substring or numeric index of the capture device
    # Model
    model: str = "base"  # tiny / base / small (or medium, or a local folder path)
    translate: bool = False  # translate other languages (e.g. Chinese) into English subtitles
    language: str = "en"  # spoken language: en, zh, ja ... or auto (detect)
    compute_type: str = "int8"  # int8 is fastest on Apple Silicon / Intel CPUs
    cpu_threads: int = 0  # 0 = let CTranslate2 decide
    beam_size: int = 1  # 1 = greedy decoding = lowest latency
    download_root: str | None = None  # where models are cached / looked up
    # Chunking / latency
    min_chunk: float = 1.0  # seconds: never transcribe less than this
    max_chunk: float = 4.0  # seconds: force a cut even if nobody pauses (live preview hides the wait)
    pause_len: float = 0.35  # seconds of quiet at the end of the buffer = "pause"
    silence_rms: float = 0.004  # RMS below this is treated as silence
    min_speech: float = 0.3  # seconds of real speech (Silero VAD) a chunk needs to be shown
    partial_interval: float = 0.6  # seconds between live "as you speak" updates (0 = off)
    # Overlay look
    font_size: int = 28
    font_family: str = "Helvetica Neue"
    text_color: str = "#FFFFFF"
    bg_color: str = "#000000"
    bg_opacity: float = 0.55  # 0.0 = fully transparent background, 1.0 = solid
    width: float = 0.70  # fraction of the screen width
    bottom_margin: int = 90  # pixels from the bottom of the screen
    max_lines: int = 2  # how many recent subtitle lines to keep on screen
    clear_after: float = 5.0  # seconds without new speech before clearing
    click_through: bool = False  # let mouse clicks pass through the overlay
    follow_mouse: bool = True  # move the overlay to whichever display the mouse is on
    # Hotkeys
    global_hotkeys: bool = True
    # Extras
    obs_file: str | None = None
    transcript: str | None = None
    extra: dict = field(default_factory=dict)


def build_arg_parser() -> argparse.ArgumentParser:
    d = Config()
    p = argparse.ArgumentParser(
        description="Offline real-time English subtitles for macOS system audio.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--config", help="JSON file with any of the options below (CLI wins)")

    g = p.add_argument_group("audio")
    g.add_argument("--device", default=d.device, help="capture device name substring or index")
    g.add_argument("--list-devices", action="store_true", help="list audio devices and exit")
    g.add_argument("--test-audio", action="store_true", help="show a live input level meter and exit")

    g = p.add_argument_group("model")
    g.add_argument("--model", default=d.model, help="tiny / base / small / medium, a model name, or a local folder")
    g.add_argument(
        "--translate",
        action="store_true",
        help="translate speech in other languages (e.g. Chinese) into English subtitles; "
        "uses the multilingual model, 'small' or better recommended",
    )
    g.add_argument(
        "--language",
        default=d.language,
        help="spoken language code: en, zh, ja, ko ... or auto. With --translate the default is auto",
    )
    g.add_argument("--compute-type", default=d.compute_type, help="int8, int8_float32, float32 ...")
    g.add_argument("--cpu-threads", type=int, default=d.cpu_threads)
    g.add_argument("--beam-size", type=int, default=d.beam_size)
    g.add_argument("--download-root", default=d.download_root, help="model cache folder")

    g = p.add_argument_group("latency")
    g.add_argument("--min-chunk", type=float, default=d.min_chunk)
    g.add_argument("--max-chunk", type=float, default=d.max_chunk)
    g.add_argument("--pause-len", type=float, default=d.pause_len)
    g.add_argument("--silence-rms", type=float, default=d.silence_rms)
    g.add_argument(
        "--min-speech",
        type=float,
        default=d.min_speech,
        help="ignore chunks with less than this many seconds of detected speech (noise, music)",
    )
    g.add_argument(
        "--partial-interval",
        type=float,
        default=d.partial_interval,
        help="show words while the sentence is still being spoken, every N seconds (0 = off)",
    )

    g = p.add_argument_group("overlay")
    g.add_argument("--font-size", type=int, default=d.font_size)
    g.add_argument("--font-family", default=d.font_family)
    g.add_argument("--text-color", default=d.text_color, help="name or hex, e.g. yellow or #FFD700")
    g.add_argument("--bg-color", default=d.bg_color)
    g.add_argument("--bg-opacity", type=float, default=d.bg_opacity, help="0.0 - 1.0")
    g.add_argument("--width", type=float, default=d.width, help="fraction of screen width")
    g.add_argument("--bottom-margin", type=int, default=d.bottom_margin)
    g.add_argument("--max-lines", type=int, default=d.max_lines)
    g.add_argument("--clear-after", type=float, default=d.clear_after)
    g.add_argument("--click-through", action="store_true", help="mouse clicks pass through (use global hotkeys)")
    g.add_argument("--no-global-hotkeys", dest="global_hotkeys", action="store_false")
    g.add_argument(
        "--no-follow-mouse",
        dest="follow_mouse",
        action="store_false",
        help="stay on the main display instead of following the mouse to other displays",
    )

    g = p.add_argument_group("optional extras")
    g.add_argument("--obs-file", default=d.obs_file, help="keep the current subtitle in this text file (for OBS)")
    g.add_argument(
        "--transcript",
        nargs="?",
        const="auto",
        default=d.transcript,
        help="save the full transcript; with no value a timestamped file name is used",
    )
    return p


def load_config(argv: list[str] | None = None) -> tuple[Config, argparse.Namespace]:
    parser = build_arg_parser()
    # First pass: only to find --config, so the JSON can become the defaults.
    pre, _ = parser.parse_known_args(argv)
    if pre.config:
        data = json.loads(Path(pre.config).expanduser().read_text())
        data = {k.replace("-", "_"): v for k, v in data.items()}
        parser.set_defaults(**data)
    args = parser.parse_args(argv)

    cfg = Config()
    for name in cfg.__dataclass_fields__:
        if hasattr(args, name):
            setattr(cfg, name, getattr(args, name))

    cfg.bg_opacity = min(max(cfg.bg_opacity, 0.0), 1.0)
    if cfg.max_chunk < cfg.min_chunk:
        cfg.max_chunk = cfg.min_chunk
    if cfg.transcript == "auto":
        cfg.transcript = f"transcript_{_dt.datetime.now():%Y%m%d_%H%M%S}.txt"
    return cfg, args


# ----------------------------------------------------------------------------
# Audio helpers
# ----------------------------------------------------------------------------
def list_devices() -> None:
    print(sd.query_devices())
    print("\nInput-capable devices (use the index or part of the name with --device):")
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            print(f"  [{i}] {dev['name']}  ({dev['max_input_channels']} ch, {int(dev['default_samplerate'])} Hz)")


def find_input_device(spec: str) -> int:
    """Return the index of the input device matching `spec` (index or name substring)."""
    devices = sd.query_devices()
    if str(spec).isdigit():
        idx = int(spec)
        if idx < len(devices) and devices[idx]["max_input_channels"] > 0:
            return idx
        raise RuntimeError(f"Device index {idx} is not an input device.")
    matches = [
        i
        for i, dev in enumerate(devices)
        if spec.lower() in dev["name"].lower() and dev["max_input_channels"] > 0
    ]
    if not matches:
        raise RuntimeError(
            f'No input device containing "{spec}" was found.\n'
            "Is BlackHole installed? Run `python live_subtitles.py --list-devices`, and see "
            "'Troubleshooting' in SETUP_GUIDE.md (a reboot or `sudo killall coreaudiod` often helps)."
        )
    return matches[0]


def resample_to_16k(x: np.ndarray, sr: int) -> np.ndarray:
    """Cheap, dependency-free resampler that is good enough for speech."""
    if sr == WHISPER_SAMPLE_RATE or len(x) == 0:
        return x
    if sr % WHISPER_SAMPLE_RATE == 0:
        # 48 kHz / 32 kHz: average every N samples (box low-pass + decimate).
        n = sr // WHISPER_SAMPLE_RATE
        usable = len(x) - (len(x) % n)
        return x[:usable].reshape(-1, n).mean(axis=1).astype(np.float32)
    # 44.1 kHz etc.: light low-pass, then linear interpolation.
    k = int(np.ceil(sr / WHISPER_SAMPLE_RATE))
    if k > 1:
        x = np.convolve(x, np.ones(k, dtype=np.float32) / k, mode="same")
    n_out = int(round(len(x) * WHISPER_SAMPLE_RATE / sr))
    t_in = np.arange(len(x), dtype=np.float64)
    t_out = np.linspace(0, len(x) - 1, n_out)
    return np.interp(t_out, t_in, x).astype(np.float32)


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0


class AudioCapture:
    """Records the loopback device and pushes 16 kHz mono float32 blocks into a queue."""

    def __init__(self, device_spec: str):
        self.device = find_input_device(device_spec)
        info = sd.query_devices(self.device)
        self.name = info["name"]
        self.samplerate = int(info["default_samplerate"])  # use the device's native rate
        self.channels = max(1, min(2, int(info["max_input_channels"])))
        self.queue: "queue.Queue[np.ndarray]" = queue.Queue()
        self.stream: sd.InputStream | None = None

    def _callback(self, indata, frames, time_info, status):  # runs on PortAudio's thread
        if status:
            print(f"[audio] {status}", file=sys.stderr)
        mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
        self.queue.put(resample_to_16k(mono.astype(np.float32, copy=True), self.samplerate))

    def start(self) -> None:
        self.stream = sd.InputStream(
            device=self.device,
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="float32",
            blocksize=int(self.samplerate * 0.1),  # 100 ms blocks
            callback=self._callback,
        )
        self.stream.start()

    def stop(self) -> None:
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None


def run_audio_test(device_spec: str, seconds: float = 15.0) -> None:
    """Print a level meter so you can confirm BlackHole is receiving sound."""
    cap = AudioCapture(device_spec)
    print(f"Listening on [{cap.device}] {cap.name} at {cap.samplerate} Hz for {seconds:.0f}s.")
    print("Play a video now. The bar should move. If it stays at 0, see Troubleshooting.\n")
    cap.start()
    t_end = time.time() + seconds
    try:
        while time.time() < t_end:
            blocks = []
            try:
                while True:
                    blocks.append(cap.queue.get(timeout=0.2))
            except queue.Empty:
                pass
            level = rms(np.concatenate(blocks)) if blocks else 0.0
            bar = "#" * min(50, int(level * 500))
            print(f"\r  RMS {level:0.4f} |{bar:<50}|", end="", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        cap.stop()
        print()


# ----------------------------------------------------------------------------
# Transcription worker
# ----------------------------------------------------------------------------
class Bridge(QObject):
    """Qt signals are the thread-safe way to hand text from the worker to the UI."""

    text = Signal(str)  # a finished subtitle line
    partial = Signal(str)  # live, still-changing text for the sentence in progress
    status = Signal(str)
    error = Signal(str)


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # Drop bracketed sound tags like [Music] or (applause).
    text = re.sub(r"[\[(][^\])]{0,30}[\])]", "", text).strip()
    return text


class Transcriber(threading.Thread):
    def __init__(self, cfg: Config, audio: AudioCapture, bridge: Bridge):
        super().__init__(name="transcriber", daemon=True)
        self.cfg = cfg
        self.audio = audio
        self.bridge = bridge
        self.stop_event = threading.Event()
        self.paused = threading.Event()
        self.model = None
        self._last_text = ""

    def load_model(self):
        from faster_whisper import WhisperModel  # imported here so --help is instant

        if self.english_only():
            # English in, English out: the ".en" models are more accurate.
            name = MODEL_ALIASES.get(self.cfg.model, self.cfg.model)
        else:
            # Translation / other languages need the multilingual model (no ".en").
            name = self.cfg.model
        self.bridge.status.emit(f"Loading model '{name}' ...")
        print(f"Loading faster-whisper model '{name}' (compute_type={self.cfg.compute_type}) ...")
        self.model = WhisperModel(
            name,
            device="cpu",  # CTranslate2 has no Metal backend; CPU int8 is fast on M-series
            compute_type=self.cfg.compute_type,
            cpu_threads=self.cfg.cpu_threads,
            download_root=self.cfg.download_root,
        )
        print("Model ready.")

    def english_only(self) -> bool:
        return not self.cfg.translate and self.cfg.language == "en"

    def spoken_language(self) -> str | None:
        lang = self.cfg.language
        if self.cfg.translate and lang == "en":
            lang = "auto"  # translating: detect what is being spoken
        return None if lang == "auto" else lang

    def speech_seconds(self, audio: np.ndarray) -> float:
        """How much real speech Silero VAD finds in `audio` (noise, music and hum score ~0)."""
        from faster_whisper.vad import VadOptions, get_speech_timestamps

        stamps = get_speech_timestamps(audio, VadOptions(threshold=0.5, min_silence_duration_ms=300))
        return sum(s["end"] - s["start"] for s in stamps) / WHISPER_SAMPLE_RATE

    def transcribe(self, audio: np.ndarray, chunk_rms: float, final: bool = True) -> str:
        # Gate: no real speech in this chunk -> no subtitle. This is what stops room noise,
        # music or a quiet microphone from producing made-up lines.
        speech = self.speech_seconds(audio)
        if speech < self.cfg.min_speech:
            return ""
        segments, _info = self.model.transcribe(
            audio,
            language=self.spoken_language(),  # "en" by default; None = auto-detect
            task="translate" if self.cfg.translate else "transcribe",  # translate -> English
            beam_size=self.cfg.beam_size,
            temperature=0.0,
            vad_filter=True,  # Silero VAD removes non-speech before decoding
            vad_parameters={"min_silence_duration_ms": 300, "speech_pad_ms": 200},
            condition_on_previous_text=False,  # avoids repetition loops on short chunks
            without_timestamps=True,
            no_speech_threshold=0.6,
        )
        parts = []
        for seg in segments:
            # Whisper's own "not speech" / "not confident" / "repeating itself" signals.
            if seg.no_speech_prob > 0.5 or seg.avg_logprob < -1.0 or seg.compression_ratio > 2.4:
                continue
            t = clean_text(seg.text)
            if t:
                parts.append(t)
        text = " ".join(parts).strip()

        # Ignore empty / punctuation-only output.
        if not re.search(r"\w", text):
            return ""
        # Ignore well-known hallucinations when the chunk was fairly quiet.
        if text.lower().strip(" .!") in {h.strip(" .!") for h in HALLUCINATIONS} and (
            chunk_rms < self.cfg.silence_rms * 4 or speech < 1.0
        ):
            return ""
        if not final:
            return text  # live preview: no de-duplication, it will be replaced anyway
        # Ignore exact repeats of the previous line.
        if text == self._last_text:
            return ""
        self._last_text = text
        return text

    def run(self) -> None:
        try:
            self.load_model()
        except Exception as exc:  # network / model-path problems
            self.bridge.error.emit(f"Could not load the model: {exc}")
            return
        # Visible hint that the app is alive; it disappears with the first subtitle.
        self.bridge.status.emit(LISTENING)

        sr = WHISPER_SAMPLE_RATE
        buf = np.zeros(0, dtype=np.float32)
        pause_samples = int(self.cfg.pause_len * sr)
        last_partial = 0.0

        while not self.stop_event.is_set():
            # Collect everything the audio thread has produced so far.
            blocks: list[np.ndarray] = []
            try:
                blocks.append(self.audio.queue.get(timeout=0.1))
                while True:
                    blocks.append(self.audio.queue.get_nowait())
            except queue.Empty:
                pass
            if not blocks:
                continue
            buf = np.concatenate([buf, *blocks])

            if self.paused.is_set():
                buf = buf[:0]  # throw audio away while paused
                continue

            dur = len(buf) / sr
            # Cut at a natural pause (quiet tail) or when the chunk is long enough.
            tail_quiet = rms(buf[-pause_samples:]) < self.cfg.silence_rms
            ready = dur >= self.cfg.min_chunk and (tail_quiet or dur >= self.cfg.max_chunk)

            if not ready:
                # Live preview: re-transcribe the growing sentence every partial_interval
                # seconds so words appear while they are spoken, not only after a pause.
                now = time.time()
                if (
                    self.cfg.partial_interval > 0
                    and dur >= 0.5
                    and now - last_partial >= self.cfg.partial_interval
                    and rms(buf) >= self.cfg.silence_rms
                ):
                    last_partial = now
                    try:
                        preview = self.transcribe(buf, rms(buf), final=False)
                    except Exception as exc:
                        print(f"[partial] {exc}", file=sys.stderr)
                        preview = ""
                    if preview and not self.paused.is_set():
                        self.bridge.partial.emit(preview)
                continue

            chunk, buf = buf, np.zeros(0, dtype=np.float32)
            chunk_rms = rms(chunk)
            if chunk_rms < self.cfg.silence_rms:
                self.bridge.partial.emit("")
                continue  # the whole chunk is silence: skip it, no blank subtitle

            t0 = time.time()
            try:
                text = self.transcribe(chunk, chunk_rms)
            except Exception as exc:
                print(f"[transcribe] {exc}", file=sys.stderr)
                continue
            if text and not self.paused.is_set():
                print(f"[{time.time() - t0:4.1f}s] {text}")
                self.bridge.text.emit(text)  # replaces the live preview
            else:
                self.bridge.partial.emit("")  # drop a preview that turned out empty

            # If we fall behind (slow model), drop the backlog to keep latency bounded.
            backlog = self.audio.queue.qsize() * 0.1
            if backlog > self.cfg.max_chunk * 2:
                dropped = 0
                try:
                    while True:
                        self.audio.queue.get_nowait()
                        dropped += 1
                except queue.Empty:
                    pass
                print(f"[lag] dropped {dropped * 0.1:.1f}s of audio; try a smaller --model", file=sys.stderr)

    def stop(self) -> None:
        self.stop_event.set()


# ----------------------------------------------------------------------------
# Optional extras: OBS text file + transcript file
# ----------------------------------------------------------------------------
class OutputFiles:
    def __init__(self, cfg: Config):
        self.obs_path = Path(cfg.obs_file).expanduser() if cfg.obs_file else None
        self.transcript = None
        if cfg.transcript:
            path = Path(cfg.transcript).expanduser()
            self.transcript = path.open("a", encoding="utf-8")
            self.transcript.write(f"\n# Live transcript started {_dt.datetime.now():%Y-%m-%d %H:%M:%S}\n")
            self.transcript.flush()
            print(f"Saving transcript to {path.resolve()}")
        if self.obs_path:
            print(f"Writing current subtitle for OBS to {self.obs_path.resolve()}")
            self.write_obs("")

    def write_obs(self, text: str) -> None:
        if not self.obs_path:
            return
        tmp = self.obs_path.with_suffix(self.obs_path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self.obs_path)  # atomic, so OBS never reads a half-written file

    def add_line(self, text: str) -> None:
        if self.transcript:
            self.transcript.write(f"[{_dt.datetime.now():%H:%M:%S}] {text}\n")
            self.transcript.flush()

    def close(self) -> None:
        if self.transcript:
            self.transcript.write(f"# Ended {_dt.datetime.now():%Y-%m-%d %H:%M:%S}\n")
            self.transcript.close()
            self.transcript = None
        self.write_obs("")


# ----------------------------------------------------------------------------
# Overlay window
# ----------------------------------------------------------------------------
class Overlay(QWidget):
    def __init__(self, cfg: Config, outputs: OutputFiles):
        super().__init__()
        self.cfg = cfg
        self.outputs = outputs
        # (text, time shown). Each line disappears clear_after seconds after it appeared,
        # so old lines never pile up on screen.
        self.lines: deque[tuple[str, float]] = deque(maxlen=max(1, cfg.max_lines))
        self.partial_time = 0.0
        self.status_text = ""
        self.partial_text = ""
        self._drag_offset: QPoint | None = None

        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        if cfg.click_through:
            flags |= Qt.WindowTransparentForInput
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)  # we paint our own background
        always_show = getattr(Qt.WidgetAttribute, "WA_MacAlwaysShowToolWindow", None)
        if always_show is not None:
            self.setAttribute(always_show)  # don't hide when another app is active

        bg = QColor(cfg.bg_color)
        bg.setAlphaF(cfg.bg_opacity)
        self.bg = bg

        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        font = QFont(cfg.font_family, cfg.font_size)
        font.setWeight(QFont.DemiBold)
        self.label.setFont(font)
        self.label.setStyleSheet(f"color: {QColor(cfg.text_color).name()}; background: transparent;")
        # A soft shadow keeps text readable even with a fully transparent background.
        shadow = QGraphicsDropShadowEffect(self.label)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 230))
        self.label.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.addWidget(self.label)

        self._screen = None
        self._place_on(QApplication.primaryScreen())

        # Every 0.7 s: follow the mouse to another display, and re-assert "on top"
        # (macOS can push the window back when you switch Spaces / go full screen).
        self.keep_timer = QTimer(self)
        self.keep_timer.timeout.connect(self._keep_visible)
        self.keep_timer.start(700)

        # Remove expired lines a few times per second.
        self.expire_timer = QTimer(self)
        self.expire_timer.timeout.connect(self._expire_lines)
        self.expire_timer.start(250)

        # Local shortcuts (overlay focused). Qt maps "Ctrl" to the Cmd key on macOS.
        for seq in ("Esc", "Ctrl+Q"):
            QShortcut(QKeySequence(seq), self, activated=QApplication.quit)

    # -- text handling ---------------------------------------------------
    def show_partial(self, text: str) -> None:
        """Show (or clear) the sentence that is still being spoken."""
        if text == self.partial_text:
            return
        self.partial_text = text
        self.partial_time = time.time()
        if text and self.status_text == LISTENING:
            self.status_text = ""
        self._render()
        self.outputs.write_obs("\n".join(self._visible_lines()))

    def _expire_lines(self) -> None:
        if self.cfg.clear_after <= 0:
            return
        cutoff = time.time() - self.cfg.clear_after
        changed = False
        while self.lines and self.lines[0][1] < cutoff:
            self.lines.popleft()
            changed = True
        if self.partial_text and self.partial_time < cutoff:
            self.partial_text = ""
            changed = True
        if changed:
            self._render()
            self.outputs.write_obs("\n".join(self._visible_lines()))

    def _visible_lines(self) -> list[str]:
        lines = [t for t, _ in self.lines]
        if self.partial_text:
            lines.append(self.partial_text)
        return lines[-max(1, self.cfg.max_lines):]

    def show_text(self, text: str) -> None:
        self.partial_text = ""
        if self.status_text == LISTENING:
            self.status_text = ""
        self.lines.append((text, time.time()))
        self._render()
        self.outputs.add_line(text)
        self.outputs.write_obs("\n".join(self._visible_lines()))

    def clear_text(self) -> None:
        self.lines.clear()
        self.partial_text = ""
        self._render()
        self.outputs.write_obs("")

    def set_status(self, msg: str) -> None:
        self.status_text = msg
        self._render()

    def _render(self) -> None:
        parts = self._visible_lines()
        if self.status_text:
            parts = [self.status_text] + parts
        self.label.setText("\n".join(parts))
        self._reflow()
        self.update()

    def _place_on(self, screen) -> None:
        """Put the bar at the bottom centre of `screen`."""
        g = screen.availableGeometry()
        self._screen = screen
        self.setFixedWidth(int(g.width() * self.cfg.width))
        self._anchor_bottom = g.bottom() - self.cfg.bottom_margin
        self._center_x = g.center().x()
        self._reflow()

    def _keep_visible(self) -> None:
        if self.cfg.follow_mouse and self._drag_offset is None:
            screen = QApplication.screenAt(QCursor.pos())
            if screen is not None and screen is not self._screen:
                self._place_on(screen)
        if self.isVisible():
            macos_raise(self)

    def _reflow(self) -> None:
        """Resize to fit the text, keeping the bottom edge where it was."""
        if not self.label.text():
            # Nothing to show: shrink to a 1-pixel strip so no empty box can linger.
            self.resize(self.width(), 1)
            self.move(int(self._center_x - self.width() / 2), int(self._anchor_bottom - 1))
            return
        self.adjustSize()
        h = max(self.sizeHint().height(), 10)
        self.resize(self.width(), h)
        self.move(int(self._center_x - self.width() / 2), int(self._anchor_bottom - h))

    # -- painting --------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        # Always wipe the window first. On macOS a translucent window keeps its old
        # pixels if we paint nothing, which left the dark box on screen after the
        # text was gone.
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        if not self.label.text():
            return  # nothing to show: stay fully invisible (no empty box)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self.bg)
        p.drawRoundedRect(self.rect(), 14, 14)

    # -- drag to move ----------------------------------------------------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_offset is not None:
            top_left = e.globalPosition().toPoint() - self._drag_offset
            self.move(top_left)
            self._center_x = top_left.x() + self.width() / 2
            self._anchor_bottom = top_left.y() + self.height()

    def mouseReleaseEvent(self, _e) -> None:
        self._drag_offset = None


def apply_macos_window_tweaks(widget: QWidget) -> None:
    """Show the overlay on every Space and above full-screen apps (needs PyObjC)."""
    if sys.platform != "darwin":
        return
    try:
        import objc
        from AppKit import (
            NSApplication,
            NSApplicationActivationPolicyAccessory,
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorFullScreenAuxiliary,
            NSWindowCollectionBehaviorStationary,
        )
    except ImportError:
        print("Tip: pip install pyobjc-framework-Cocoa to show the overlay over full-screen videos.")
        return
    try:
        # A regular app's windows cannot float over another app's full-screen Space
        # (e.g. Chrome/YouTube full screen). An "accessory" app (no Dock icon) can.
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        view = objc.objc_object(c_void_p=int(widget.winId()))
        window = view.window()
        window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorStationary
        )
        # Non-activating panel: may sit over another app's full-screen Space without
        # stealing focus (NSWindowStyleMaskNonactivatingPanel = 1 << 7).
        window.setStyleMask_(window.styleMask() | (1 << 7))
        window.setHidesOnDeactivate_(False)
        # No system shadow: macOS draws it around the window's last content, which can
        # leave a ghost of the box behind when the subtitle is empty.
        window.setHasShadow_(False)
        window.setOpaque_(False)
        macos_raise(widget)
    except Exception as exc:
        print(f"(macOS window tweaks skipped: {exc})")


def macos_raise(widget: QWidget) -> None:
    """Float above everything, including full-screen Chrome, and bring the bar to the front."""
    if sys.platform != "darwin":
        return
    try:
        import objc
        from AppKit import NSPopUpMenuWindowLevel

        window = objc.objc_object(c_void_p=int(widget.winId())).window()
        if window.level() != NSPopUpMenuWindowLevel:
            window.setLevel_(NSPopUpMenuWindowLevel)
        window.orderFrontRegardless()  # works even though we are never the active app
    except Exception:
        pass


class GlobalHotkeys:
    """System-wide Ctrl+Option+<key> shortcuts using a listen-only Quartz event tap.

    The tap is attached to the main run loop, which Qt's Cocoa event loop drives, so the
    callbacks run on the main (GUI) thread. Requires Input Monitoring permission for the
    app that launches Python (Terminal, iTerm, VS Code ...).
    """

    KEYCODES = {"q": 12, "p": 35, "h": 4}  # ANSI virtual key codes

    def __init__(self, actions: dict[str, callable]):
        self._refs = None
        if sys.platform != "darwin":
            return
        try:
            import Quartz
        except ImportError:
            print("Tip: pip install pyobjc-framework-Quartz for global hotkeys.")
            return
        by_code = {self.KEYCODES[k]: fn for k, fn in actions.items()}
        need = Quartz.kCGEventFlagMaskControl | Quartz.kCGEventFlagMaskAlternate

        def handler(proxy, etype, event, refcon):
            try:
                if etype in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
                    Quartz.CGEventTapEnable(self._refs[0], True)
                    return event
                code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
                flags = Quartz.CGEventGetFlags(event)
                if (flags & need) == need and code in by_code:
                    by_code[code]()
            except Exception as exc:
                print(f"[hotkey] {exc}", file=sys.stderr)
            return event

        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown),
            handler,
            None,
        )
        if tap is None:
            print(
                "Global hotkeys are off: grant Input Monitoring to your terminal app in\n"
                "System Settings > Privacy & Security > Input Monitoring, then restart it.\n"
                "(Esc / Cmd+Q on the focused overlay and Ctrl+C in the terminal still work.)"
            )
            return
        source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetMain(), source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(tap, True)
        self._refs = (tap, source, handler)  # keep alive
        print("Global hotkeys: Ctrl+Option+Q quit, Ctrl+Option+P pause, Ctrl+Option+H hide/show")

    def close(self) -> None:
        if self._refs:
            import Quartz

            Quartz.CGEventTapEnable(self._refs[0], False)
            self._refs = None


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
_instance_lock = None


def acquire_single_instance_lock() -> bool:
    """Only one overlay at a time, so windows can't stack on top of each other."""
    global _instance_lock
    try:
        import fcntl
    except ImportError:  # not on macOS/Linux
        return True
    import tempfile

    path = Path(tempfile.gettempdir()) / "live_subtitles.lock"
    _instance_lock = open(path, "w")
    try:
        fcntl.flock(_instance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    _instance_lock.write(str(os.getpid()))
    _instance_lock.flush()
    return True


def main(argv: list[str] | None = None) -> int:
    cfg, args = load_config(argv)

    if args.list_devices:
        list_devices()
        return 0
    if args.test_audio:
        run_audio_test(cfg.device)
        return 0

    if not acquire_single_instance_lock():
        print(
            "Live Subtitles is already running. Quit it first (Ctrl+Option+Q, or\n"
            "`pkill -f live_subtitles.py`), then start it again.",
            file=sys.stderr,
        )
        return 1

    try:
        audio = AudioCapture(cfg.device)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"Capturing from [{audio.device}] {audio.name} ({audio.samplerate} Hz, {audio.channels} ch)")

    app = QApplication(sys.argv[:1])
    if sys.platform == "darwin":
        # Become an accessory app (no Dock icon) BEFORE any window exists, so the overlay
        # can join other apps' full-screen Spaces (e.g. full-screen Chrome / YouTube).
        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

            NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception as exc:
            print(f"(activation policy not set: {exc})")
    app.setApplicationName("Live Subtitles")
    app.setQuitOnLastWindowClosed(True)

    outputs = OutputFiles(cfg)
    overlay = Overlay(cfg, outputs)
    bridge = Bridge()
    worker = Transcriber(cfg, audio, bridge)

    def toggle_pause() -> None:
        if worker.paused.is_set():
            worker.paused.clear()
            overlay.set_status("")
            print("Resumed.")
        else:
            worker.paused.set()
            overlay.clear_text()
            overlay.set_status("⏸ Paused")
            print("Paused.")

    def toggle_visible() -> None:
        overlay.setVisible(not overlay.isVisible())

    def on_error(msg: str) -> None:
        print(msg, file=sys.stderr)
        overlay.set_status("⚠ " + msg[:120])

    bridge.text.connect(overlay.show_text)
    bridge.partial.connect(overlay.show_partial)
    bridge.status.connect(overlay.set_status)
    bridge.error.connect(on_error)
    for seq in ("Ctrl+P",):  # (no plain Space: it clashes with video players' play/pause)
        QShortcut(QKeySequence(seq), overlay, activated=toggle_pause)

    hotkeys = GlobalHotkeys({"q": app.quit, "p": toggle_pause, "h": toggle_visible}) if cfg.global_hotkeys else None

    # Clean shutdown, whichever way we quit.
    def shutdown() -> None:
        print("\nShutting down ...")
        # Watchdog: if anything below hangs (audio driver, a long transcription),
        # force the process to exit after 3 seconds so quitting always works.
        watchdog = threading.Timer(3.0, lambda: os._exit(0))
        watchdog.daemon = True
        watchdog.start()
        worker.stop()
        audio.stop()
        worker.join(timeout=2)
        if hotkeys:
            hotkeys.close()
        outputs.close()

    app.aboutToQuit.connect(shutdown)

    # Ctrl+C in the terminal: Qt blocks Python signal handling, so wake Python up
    # regularly with a no-op timer and quit the Qt loop from the handler.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    tick = QTimer()
    tick.start(200)
    tick.timeout.connect(lambda: None)

    overlay.show()
    apply_macos_window_tweaks(overlay)
    # Re-apply shortly after start-up: macOS can reset the level when the window first maps.
    QTimer.singleShot(800, lambda: apply_macos_window_tweaks(overlay))
    audio.start()
    worker.start()
    print("Running. Play some audio. Quit with Ctrl+Option+Q, Esc on the overlay, or Ctrl+C here.")
    code = app.exec()
    sys.stdout.flush()
    sys.stderr.flush()
    # Exit right away: background threads of the speech engine or audio driver must
    # not keep the process (and the overlay) alive after quitting.
    os._exit(code)


if __name__ == "__main__":
    sys.exit(main())
