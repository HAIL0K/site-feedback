---
name: site-feedback
description: Use when the person wants to show you changes instead of typing them - "let's do site feedback", "I'll record my screen", "let me show you what to change", "record me", "I'll talk you through it". Opens a small recording bar; they talk and draw on the screen; you get a timeline of what they said plus their marked-up screenshots, and turn it into changes.
---

# Site feedback

The person talks through what they want changed while looking at their screen, and
draws on it. You get the result as a file. They should never see a terminal, a file
path or an error message they have to act on: you handle all of that.

## 1. Start the recorder

If this is their first time, first say in one sentence what will happen ("A small bar
will appear; talk me through the changes, click Draw to point at things, Stop when
done") so the bar doesn't surprise them.

Run this in the background (Claude Code: Bash with `run_in_background: true`, because
the recording can last longer than a normal command timeout):

```
"{{PYTHON}}" -m site_feedback record
```

Then tell the person, in these words or close to them:

> A small dark bar with Draw and Stop just appeared in the top-right of your screen.
> Talk me through everything you want changed, like you would to a person sitting
> next to you. Whenever you want to point at something, click Draw, circle or
> scribble on it, and click Done. You can drag the bar to the screen your site is on.
> Click Stop when you're finished. The bar says "Done" when I have it.

Don't poll while they talk. You are notified when the command exits.

## 2. Read what came back

The last line of output is `FEEDBACK READY: <path to feedback.md>`. Read that file, then
open every Drawing image it lists, and any `screen:` image next to a line that says
"this", "here" or "that" without naming the thing.

## 3. Confirm, then change

Write a short numbered list of concrete changes in plain language, one per thing they
asked for, with the time it was said ("3. Make the Get started button blue (01:32)").
Merge repeats; leave out thinking-aloud that isn't a request. Ask: "Is that everything,
and is anything wrong?" Make the changes only after they answer.

## If something goes wrong

- Output says `No speech was picked up`: the microphone is muted or the wrong one is the
  system default. Ask them to check it, then record again.
- Run `"{{PYTHON}}" -m site_feedback check` to test the window, screen capture and mic.
- macOS, screenshots are only the desktop wallpaper or blank: Screen Recording isn't
  allowed for the app running you. System Settings > Privacy & Security > Screen Recording,
  turn it on for that app, quit and reopen it.
- Transcription failed but the recording finished: the session folder is kept. Run
  `"{{PYTHON}}" -m site_feedback transcribe <session folder>`.
- Not installed (the python path above doesn't exist): run `python install.py` in the
  site-feedback folder.
