"""site-feedback: record your screen and voice, draw on it, hand the result to your agent.

  python -m site_feedback record [--out DIR] [--no-transcribe] [--selftest]
  python -m site_feedback transcribe SESSION_DIR
  python -m site_feedback check
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

DEFAULT_MODEL = os.environ.get("SITE_FEEDBACK_MODEL", "small")
DEVICE = os.environ.get("SITE_FEEDBACK_DEVICE", "cpu")


def say(msg: str):
    print(msg, flush=True)


def load_wav_16k(path: Path):
    """Our own 16-bit WAV as float32 mono at 16 kHz.

    Decoding it ourselves keeps PyAV out of the path: PyAV 16 dropped the
    `metadata_errors` argument faster-whisper passes (TypeError seen 2026-10-27).
    """
    import wave

    import numpy as np

    with wave.open(str(path), "rb") as w:
        rate, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if rate != 16000 and len(x):
        n = int(len(x) * 16000 / rate)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return x


def transcribe_audio(wav: Path) -> tuple[list[dict], str]:
    from faster_whisper import WhisperModel

    model = WhisperModel(DEFAULT_MODEL, device=DEVICE, compute_type="int8")
    segs, info = model.transcribe(load_wav_16k(wav), vad_filter=True, beam_size=5)
    return [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs], info.language


def finish(session_dir: Path, transcribe: bool = True) -> Path:
    from .timeline import build_markdown

    meta_path = session_dir / "session.json"
    session = json.loads(meta_path.read_text(encoding="utf-8"))
    wav = session_dir / "audio.wav"
    if transcribe and wav.exists() and wav.stat().st_size > 1000:
        say("Transcribing (runs on this computer, nothing is uploaded)...")
        t = time.monotonic()
        session["segments"], session["language"] = transcribe_audio(wav)
        say(f"Transcribed {len(session['segments'])} lines in {time.monotonic() - t:.0f}s.")
    meta_path.write_text(json.dumps(session, indent=2), encoding="utf-8")
    md = session_dir / "feedback.md"
    md.write_text(build_markdown(session), encoding="utf-8")
    return md


def cmd_record(args) -> int:
    from .capture import Recorder
    from .gui import App, make_dpi_aware

    make_dpi_aware()
    stamp = datetime.now()
    out = Path(args.out) if args.out else Path.home() / "site-feedback" / stamp.strftime("%Y-%m-%d_%H%M%S")
    rec = Recorder(out, audio=not args.no_audio)

    def on_stop() -> Path:
        # Runs in a worker thread while the bar shows "Sending to your agent".
        duration = rec.stop()
        session = {"started_at": stamp.strftime("%Y-%m-%d %H:%M"), "duration": round(duration, 1),
                   "frames": rec.frames, "drawings": rec.drawings, "segments": []}
        (out / "session.json").write_text(json.dumps(session, indent=2), encoding="utf-8")
        say(f"Stopped after {duration:.0f}s: {len(rec.drawings)} drawings, {len(rec.frames)} screenshots.")
        return finish(out, transcribe=not args.no_transcribe and not args.no_audio)

    app = App(rec, on_stop)
    if args.selftest:
        app.selftest(out)
    rec.start()
    say(f"Recording. Session folder: {out}")
    md = app.run()
    if md is None:  # window closed some other way before Stop
        md = on_stop()
    say(f"FEEDBACK READY: {md}")
    return 0


def cmd_transcribe(args) -> int:
    md = finish(Path(args.session))
    say(f"FEEDBACK READY: {md}")
    return 0


def cmd_check(args) -> int:
    from .gui import make_dpi_aware

    make_dpi_aware()
    ok = True
    try:
        import tkinter
        r = tkinter.Tk()
        r.withdraw()
        say(f"ok   windows: Tk {tkinter.TkVersion}, screen {r.winfo_screenwidth()}x{r.winfo_screenheight()}")
        r.destroy()
    except Exception as e:
        ok = False
        say(f"FAIL windows: {e}. On a Mac, install Python from python.org (it includes Tk).")
    try:
        from .capture import MSS, grab, monitor_at
        with MSS() as sct:
            img = grab(sct, monitor_at(sct, -10**6, -10**6))
        colours = len(img.convert("L").resize((64, 36)).getcolors(4096) or [])
        say(f"ok   screen capture: {img.width}x{img.height}")
        if sys.platform == "darwin" and colours < 8:
            say("WARN screenshot looks blank: allow Screen Recording for this app in System Settings, then restart it.")
    except Exception as e:
        ok = False
        say(f"FAIL screen capture: {e}")
    try:
        import sounddevice as sd
        say(f"ok   microphone: {sd.query_devices(kind='input')['name']}")
    except Exception as e:
        ok = False
        say(f"FAIL microphone: {e}")
    try:
        import faster_whisper  # noqa: F401
        say("ok   transcription library")
    except Exception as e:
        ok = False
        say(f"FAIL transcription library: {e}")
    say("ALL OK" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="site_feedback", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record", help="open the recording bar; blocks until Stop is clicked")
    r.add_argument("--out", help="session folder (default ~/site-feedback/<date_time>)")
    r.add_argument("--no-transcribe", action="store_true")
    r.add_argument("--no-audio", action="store_true", help="skip the microphone (testing)")
    r.add_argument("--selftest", action="store_true", help="scripted 9-second run that draws a circle")
    t = sub.add_parser("transcribe", help="re-run transcription on a session folder")
    t.add_argument("session")
    sub.add_parser("check", help="test window, screen capture, microphone and transcription setup")
    args = p.parse_args(argv)
    return {"record": cmd_record, "transcribe": cmd_transcribe, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
