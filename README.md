# site-feedback

Show your agent what to change instead of typing it. You talk through your website (or
anything on screen) and draw on it. When you click Stop, your agent gets a timeline of what
you said with your marked-up screenshots, and turns it into a list of changes for you to
confirm.

Windows and macOS. Everything runs on your computer: the transcription is local Whisper,
and nothing is uploaded.

## For the person

Give your agent this folder and say:

> Set up site-feedback from this folder for me.

After that, whenever you want to give feedback, say "let's do site feedback". A small bar
appears with Draw and Stop buttons. Talk, click Draw to circle things, click Stop when done.

## For the agent

Setup, once: `python install.py` (Python 3.10+ with Tk; on macOS use the python.org
installer). It creates `.venv`, installs the tool, downloads the speech model, installs the
skill to `~/.claude/skills/site-feedback/`, and runs `site_feedback check`. On macOS the
person must approve the Screen Recording and Microphone prompts for the app you run in, then
reopen it.

After setup, follow `skill/SKILL.md`. Agents other than Claude Code: run the record command
it names and wait for it to exit (it blocks until the person clicks Stop), then read the
`feedback.md` path it prints.

Commands (`<venv python> -m site_feedback ...`):

| Command | What it does |
|---|---|
| `record` | Bar + recording; on Stop, transcribes and prints `FEEDBACK READY: <feedback.md>` |
| `record --selftest` | Scripted 9-second run that draws a circle by itself |
| `transcribe <session>` | Re-run transcription on a kept session folder |
| `check` | Tests the window, screen capture, microphone and transcription |

Sessions are saved to `~/site-feedback/<date_time>/`: `audio.wav`, `shots/` (background
screenshots every 4 s when the screen changed, plus one marked-up image per drawing),
`session.json`, `feedback.md`.

Settings by environment variable: `SITE_FEEDBACK_MODEL` (Whisper model, default `small`;
`base` is faster, `medium` more accurate), `SITE_FEEDBACK_DEVICE` (`cpu` default, `cuda` for
an NVIDIA GPU).

## How drawing works

Draw freezes the screen: it takes a screenshot of the monitor the bar is on and shows it
full-screen with a red border. You draw on that picture, and Done drawing saves it and puts
you back. This works the same on Windows and macOS, without transparent-window tricks, and the
saved image is exactly what you saw. Scroll or click on your site between drawings, not
during one.
