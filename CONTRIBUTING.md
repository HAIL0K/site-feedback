# Contributing

Issues and pull requests are welcome.

## Reporting a problem

Open an issue with the bug template. The most useful thing you can paste is the output of:

```
<venv python> -m site_feedback check
```

plus your OS version and how many screens you have. Please don't attach session folders
or screenshots without looking at them first: they contain whatever was on your screen.

## Changing code

```
python install.py                 # or: python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m pytest -q     # Windows: .venv\Scripts\python -m pytest -q
.venv/bin/python -m site_feedback record --selftest   # 9-second scripted run, draws a circle
```

- A bug fix comes with a test that fails without the fix. Name the symptom in a comment.
- Keep it dependency-light and local: no cloud services, nothing uploaded.
- The person using this is often not technical. Anything they see (the bar, messages
  from `check`, the words the skill tells the agent to say) should make sense to them.
- macOS help is especially welcome: the maintainers develop on Windows.
