"""One-time setup, run by the agent:  python install.py

Creates .venv here, installs the tool, downloads the speech model, installs the
Claude Code skill, and runs the self-check. Standard library only, so any
Python 3.10+ can run it. Safe to run again.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
SKILL_DIR = Path.home() / ".claude" / "skills" / "site-feedback"
MODEL = os.environ.get("SITE_FEEDBACK_MODEL", "small")


def step(msg):
    print(f"\n== {msg}", flush=True)


def run(*cmd):
    # The Hugging Face cache warns about symlinks on Windows without Developer Mode; harmless.
    env = {**os.environ, "HF_HUB_DISABLE_SYMLINKS_WARNING": "1"}
    subprocess.run([str(c) for c in cmd], check=True, env=env)


def main() -> int:
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is needed. Install it from https://www.python.org/downloads/")
        return 1
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("This Python has no Tk (window toolkit). On a Mac install Python from "
              "https://www.python.org/downloads/ (Homebrew Python: brew install python-tk), then run this again.")
        return 1

    step("Creating the environment")
    if not PY.exists():
        run(sys.executable, "-m", "venv", VENV)
    run(PY, "-m", "pip", "install", "-q", "--upgrade", "pip")
    run(PY, "-m", "pip", "install", "-q", "-e", ROOT)

    step(f"Downloading the speech model ({MODEL}, a few hundred MB, once)")
    run(PY, "-c", f"from faster_whisper import WhisperModel; WhisperModel('{MODEL}', device='cpu', compute_type='int8')")

    step("Installing the Claude Code skill")
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    text = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8").replace("{{PYTHON}}", str(PY))
    (SKILL_DIR / "SKILL.md").write_text(text, encoding="utf-8")
    print(f"skill -> {SKILL_DIR / 'SKILL.md'}")

    step("Checking window, screen capture and microphone")
    if sys.platform == "darwin":
        print("On a Mac, approve the Screen Recording and Microphone prompts for the app running your agent\n"
              "(Terminal, iTerm, VS Code, Cursor...). macOS then asks to quit and reopen that app: do it, then\n"
              "run `python install.py` once more.")
    ok = subprocess.run([str(PY), "-m", "site_feedback", "check"]).returncode == 0
    print("\nSETUP DONE" if ok else "\nSETUP FINISHED WITH PROBLEMS (see above)")
    print(f"Record with: \"{PY}\" -m site_feedback record")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
