# Instructions for the agent

The person who gave you this repo wants to show you changes to their website (or any app)
by talking and drawing on their screen, instead of typing. Assume they are not technical.
They should never need to open a terminal, read a file path or fix an error themselves.
Speak to them in plain words, one short step at a time.

## Setting it up

1. If you are not already inside a permanent copy, clone the repo to `~/Tools/site-feedback`
   (not a temp folder: the installed skill points at this folder's `.venv`; and not
   `~/site-feedback`, which is where recordings are saved).
2. Check for Python 3.10+ with Tk (`python3 -c "import tkinter"`). If it is missing,
   install it for them where you can (Windows: `winget install Python.Python.3.12`;
   macOS: the python.org installer, since Homebrew Python lacks Tk unless
   `brew install python-tk` is added). If you can't install it yourself, tell them exactly
   what to click.
3. Run `python install.py` from the repo folder. It takes a few minutes (it downloads a
   speech model once). While it runs, tell them:
   > I'm setting up the recorder. It downloads a speech model once, so this takes a few minutes.
4. **macOS only.** During or after setup, macOS shows two permission prompts, for the
   microphone and for Screen Recording, for the app you are running in (Terminal, iTerm,
   VS Code, Cursor, the Claude app...). Tell them:
   > Your Mac is going to ask whether this app may use the microphone and record the screen.
   > Click Allow for both. For Screen Recording it may open System Settings: switch the
   > toggle on next to the app's name. Then the Mac asks to quit and reopen the app. Say yes,
   > open it again and tell me "done".
   Then run `python install.py` once more and check it ends with `SETUP DONE`.
5. If the check reports a problem, fix what you can and explain the rest in one sentence
   each (for example "your computer has no microphone selected").
6. Explain how to use it, in these words or close to them:
   > It's ready. Whenever you want to show me changes, just say "let's do site feedback".
   > A small dark bar appears in the top-right corner of your screen with Draw and Stop.
   > Talk me through what you want changed, like you would to someone sitting next to you.
   > To point at something, click Draw, circle it with your mouse, and click Done.
   > Click Stop when you're finished. I'll show you a list of the changes before I make any.
   >
   > Everything stays on your computer. The recorder takes screenshots of the whole screen
   > the bar is on, so keep private things on another screen while you record.
7. Offer a 30-second practice run. If they say yes, follow the usage steps below.

## Using it

Claude Code: the installer added a `site-feedback` skill; follow it. Other agents: follow
`skill/SKILL.md`, replacing `{{PYTHON}}` with this repo's `.venv` Python
(`.venv/Scripts/python.exe` on Windows, `.venv/bin/python` on macOS). The record command
blocks until they click Stop, so run it in the background or with a long timeout
(recordings can be 10 minutes or more).

## Working on the code

See `CONTRIBUTING.md`. Tests: `.venv/<bin>/python -m pytest -q`. Scripted run:
`python -m site_feedback record --selftest`.
