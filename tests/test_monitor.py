from site_feedback.capture import monitor_at


class FakeSct:
    # Layout seen 2026-10-27: the primary screen is listed AFTER the secondary one.
    monitors = [
        {"left": 0, "top": 0, "width": 3840, "height": 1200},
        {"left": 1920, "top": 115, "width": 1920, "height": 1080, "is_primary": False},
        {"left": 0, "top": 0, "width": 1920, "height": 1200, "is_primary": True},
    ]


def test_point_on_primary_returns_primary_not_monitors_1():
    assert monitor_at(FakeSct, 1800, 60)["is_primary"] is True


def test_point_on_secondary_returns_secondary():
    assert monitor_at(FakeSct, 2500, 500)["left"] == 1920


def test_point_off_every_screen_falls_back_to_primary():
    assert monitor_at(FakeSct, -5000, -5000)["is_primary"] is True
