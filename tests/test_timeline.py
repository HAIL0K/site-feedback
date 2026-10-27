from site_feedback.timeline import build_markdown, clock, frame_at

FRAMES = [{"t": 0.0, "path": "shots/frame-0000.jpg"}, {"t": 8.0, "path": "shots/frame-0008.jpg"}]


def test_clock():
    assert clock(0) == "00:00"
    assert clock(92.7) == "01:32"


def test_frame_at_picks_last_frame_not_after_time():
    assert frame_at(FRAMES, 3) == "shots/frame-0000.jpg"
    assert frame_at(FRAMES, 8) == "shots/frame-0008.jpg"
    assert frame_at([], 3) is None


def test_drawing_placed_between_the_lines_around_it():
    md = build_markdown({
        "started_at": "2026-10-27 14:00", "duration": 20,
        "segments": [{"start": 1, "end": 4, "text": "the header is too big"},
                     {"start": 10, "end": 13, "text": "and this button should be blue"}],
        "drawings": [{"n": 1, "t_start": 9, "t_end": 12, "path": "shots/draw-01.png"}],
        "frames": FRAMES,
    })
    body = md.split("## Timeline", 1)[1]
    assert body.index("too big") < body.index("Drawing 1") < body.index("should be blue")
    assert "![Drawing 1](shots/draw-01.png)" in md
    assert "(00:20 long)" in md


def test_screen_reference_only_when_it_changes():
    md = build_markdown({"segments": [{"start": 1, "end": 2, "text": "a"}, {"start": 3, "end": 4, "text": "b"},
                                      {"start": 9, "end": 10, "text": "c"}], "frames": FRAMES})
    assert md.count("frame-0000.jpg") == 1
    assert md.count("frame-0008.jpg") == 1


def test_silence_says_check_the_microphone():
    assert "No speech was picked up" in build_markdown({"segments": []})
