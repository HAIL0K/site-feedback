"""Turn a recorded session (transcript + screenshots) into feedback.md for an agent.

Pure functions, no I/O beyond what the caller passes in, so they are unit-tested.
"""
from __future__ import annotations


def clock(t: float) -> str:
    t = max(0, int(t))
    return f"{t // 60:02d}:{t % 60:02d}"


def frame_at(frames: list[dict], t: float) -> str | None:
    """Path of the last periodic frame taken at or before t (the screen being looked at)."""
    best = None
    for f in frames:
        if f["t"] <= t + 0.5:
            best = f["path"]
        else:
            break
    return best


AGENT_NOTE = """\
For the agent: a person recorded themselves talking through changes they want while
looking at their screen. Lines below are what they said, with the time. Each
"Drawing" image is the screen at that moment with their marks in red; what they say
just before, during and after a drawing is about that drawing. A spoken line names
the screen that was showing when it was said; open that image when the words alone
are ambiguous ("this", "here", "that one"). The transcript is machine-made and can
mishear names and numbers: trust the images over the words when they disagree.

Your job: turn this into a short numbered list of concrete changes in plain language,
show it to the person and let them correct it, then make the changes.
"""


def build_markdown(session: dict) -> str:
    segments = sorted(session.get("segments", []), key=lambda s: s["start"])
    drawings = sorted(session.get("drawings", []), key=lambda d: d["t_start"])
    frames = sorted(session.get("frames", []), key=lambda f: f["t"])

    out = [f"# Site feedback, {session.get('started_at', '')} ({clock(session.get('duration', 0))} long)", ""]
    out += [AGENT_NOTE, ""]

    if drawings:
        out.append("## Drawings")
        for d in drawings:
            out.append(f"- Drawing {d['n']} at {clock(d['t_start'])}: `{d['path']}`")
        out.append("")

    out.append("## Timeline")
    out.append("")
    if not segments:
        out.append("_No speech was picked up. Check that the right microphone is selected and not muted._")
        out.append("")

    events = [("say", s["start"], s) for s in segments] + [("draw", d["t_start"], d) for d in drawings]
    # A drawing sorts before speech starting at the same instant: the image is what the words refer to.
    events.sort(key=lambda e: (e[1], 0 if e[0] == "draw" else 1))

    last_screen = None
    for kind, _, item in events:
        if kind == "draw":
            out.append(
                f"> Drawing {item['n']} ({clock(item['t_start'])}-{clock(item['t_end'])}): "
                f"![Drawing {item['n']}]({item['path']})"
            )
            out.append("")
            continue
        line = f"**{clock(item['start'])}** {item['text']}"
        screen = frame_at(frames, item["start"])
        if screen and screen != last_screen:
            line += f"  _(screen: `{screen}`)_"
            last_screen = screen
        out.append(line)
        out.append("")

    return "\n".join(out).rstrip() + "\n"
