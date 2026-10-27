"""Screen and microphone capture. Same code on Windows and macOS."""
from __future__ import annotations

import queue
import threading
import time
import wave
from pathlib import Path

import mss
from PIL import Image, ImageChops, ImageStat

FRAME_EVERY = 4.0      # seconds between background screenshots
FRAME_CHANGE = 3.0     # mean grey-level difference (0-255) that counts as "the screen changed"
FRAME_MAX_WIDTH = 1600


MSS = getattr(mss, "MSS", None) or mss.mss  # mss 10 renamed the class


def monitor_at(sct, x: int, y: int) -> dict:
    """The monitor containing point (x, y); the primary one if none does.

    monitors[0] is the whole desktop and monitors[1] is NOT always the primary
    (seen 2026-10-27 on a two-screen Windows setup: the overlay showed the other screen).
    """
    mons = sct.monitors[1:]
    for m in mons:
        if m["left"] <= x < m["left"] + m["width"] and m["top"] <= y < m["top"] + m["height"]:
            return m
    return next((m for m in mons if m.get("is_primary")), mons[0])


def grab(sct, monitor: dict) -> Image.Image:
    shot = sct.grab(monitor)
    return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def shrink(img: Image.Image, width: int = FRAME_MAX_WIDTH) -> Image.Image:
    if img.width <= width:
        return img
    return img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)


class AudioWriter:
    """Records the default microphone to a mono 16-bit WAV at the device's own rate."""

    def __init__(self, path: Path):
        import sounddevice as sd

        try:
            dev = sd.query_devices(kind="input")
        except Exception as e:  # no input device at all
            raise RuntimeError("No microphone found. Plug one in or pick one in the system sound settings.") from e
        self.rate = int(dev["default_samplerate"])
        self.device_name = dev["name"]
        self._q: queue.Queue = queue.Queue()
        self._done = threading.Event()
        self._wav = wave.open(str(path), "wb")
        self._wav.setnchannels(1)
        self._wav.setsampwidth(2)
        self._wav.setframerate(self.rate)
        self._stream = sd.InputStream(samplerate=self.rate, channels=1, dtype="int16",
                                      callback=lambda data, *_: self._q.put(data.copy()))
        self._thread = threading.Thread(target=self._write, daemon=True)

    def _write(self):
        while not (self._done.is_set() and self._q.empty()):
            try:
                self._wav.writeframes(self._q.get(timeout=0.2).tobytes())
            except queue.Empty:
                pass
        self._wav.close()

    def start(self):
        self._thread.start()
        self._stream.start()

    def stop(self):
        self._stream.stop()
        self._stream.close()
        self._done.set()
        self._thread.join()


class Recorder:
    """Owns the session folder: audio.wav, shots/frame-*.jpg, shots/draw-*.png."""

    def __init__(self, out_dir: Path, audio: bool = True):
        self.out = Path(out_dir)
        (self.out / "shots").mkdir(parents=True, exist_ok=True)
        self.frames: list[dict] = []
        self.drawings: list[dict] = []
        self.drawing = threading.Event()   # set while the draw overlay is up: the screen is frozen
        self.point = (0, 0)                # centre of the bar; the monitor it is on is the one recorded
        self._stop = threading.Event()
        self._audio = AudioWriter(self.out / "audio.wav") if audio else None
        self._frames_thread = threading.Thread(target=self._frame_loop, daemon=True)
        self.t0 = 0.0

    def now(self) -> float:
        return time.monotonic() - self.t0

    def start(self):
        self.t0 = time.monotonic()
        if self._audio:
            self._audio.start()
        self._frames_thread.start()

    def stop(self) -> float:
        duration = self.now()
        self._stop.set()
        self._frames_thread.join()
        if self._audio:
            self._audio.stop()
        return duration

    def _frame_loop(self):
        last = None
        with MSS() as sct:
            while True:
                if not self.drawing.is_set():
                    t = self.now()
                    img = grab(sct, monitor_at(sct, *self.point))
                    sig = img.convert("L").resize((96, 54))
                    if last is None or ImageStat.Stat(ImageChops.difference(sig, last)).mean[0] > FRAME_CHANGE:
                        rel = f"shots/frame-{int(t):04d}.jpg"
                        shrink(img).save(self.out / rel, quality=80)
                        self.frames.append({"t": round(t, 2), "path": rel})
                        last = sig
                if self._stop.wait(FRAME_EVERY):
                    return

    def save_drawing(self, img: Image.Image, t_start: float, t_end: float):
        n = len(self.drawings) + 1
        rel = f"shots/draw-{n:02d}.png"
        shrink(img).save(self.out / rel)
        self.drawings.append({"n": n, "t_start": round(t_start, 2), "t_end": round(t_end, 2), "path": rel})
