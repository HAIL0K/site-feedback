"""The two windows the person sees: a small floating bar, and the draw overlay.

Drawing works on a frozen screenshot shown full-screen, not on a transparent window.
That behaves the same on Windows and macOS (no click-through or transparency tricks),
and the marked-up image is exactly what was on screen.
"""
from __future__ import annotations

import math
import os
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk

from . import ui
from .capture import MSS, Recorder, grab, monitor_at

BAR_W, BAR_H = 292, 52
TOOL_H = 52


def make_dpi_aware():
    """Windows: real pixels for Tk, so window coordinates match screenshot pixels. Call before Tk()."""
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


def hide_from_capture(root: tk.Tk):
    """Windows 10 2004+: keep the bar out of the screenshots. No-op elsewhere."""
    if sys.platform == "win32" and not os.environ.get("SITE_FEEDBACK_SHOW_IN_CAPTURE"):
        import ctypes
        try:
            hwnd = int(root.wm_frame(), 16)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)  # WDA_EXCLUDEFROMCAPTURE
        except Exception:
            pass


class Overlay:
    def __init__(self, root: tk.Tk, shot: Image.Image, mon: dict, on_close):
        self.shot = shot
        self.on_close = on_close
        self.strokes: list[list[tuple[int, int]]] = []
        self.items: list[list[int]] = []

        # Tk and mss share one coordinate space: points on macOS, physical pixels on
        # Windows (the process is made DPI-aware before Tk starts). The shot can be
        # larger than the monitor rect (Retina), hence the scale factors.
        sw, sh = mon["width"], mon["height"]
        self.sx, self.sy = shot.width / sw, shot.height / sh

        top = self.top = tk.Toplevel(root)
        top.overrideredirect(True)
        top.geometry(f"{sw}x{sh}+{mon['left']}+{mon['top']}")
        top.attributes("-topmost", True)
        c = self.canvas = tk.Canvas(top, width=sw, height=sh, highlightthickness=0, cursor="crosshair", bg="black")
        c.pack(fill="both", expand=True)
        self.photo = ImageTk.PhotoImage(shot.resize((sw, sh)))
        c.create_image(0, 0, anchor="nw", image=self.photo)
        c.create_rectangle(1, 1, sw - 2, sh - 2, outline=ui.RED, width=3)

        # Floating toolbar, top centre. Width follows the hint text: font sizes differ by OS.
        hint = "Draw on anything. Keep talking."
        text_w = tkfont.Font(font=ui.font(11)).measure(hint)
        tool_w = 36 + text_w + 20 + 84 + 6 + 88 + 10
        x0, y0 = (sw - tool_w) // 2, 18
        self.tool_box = (x0, y0, x0 + tool_w, y0 + TOOL_H)
        self.tool_img = ui.panel_image(tool_w, TOOL_H, keyed=False)
        c.create_image(x0, y0, anchor="nw", image=self.tool_img)
        c.create_oval(x0 + 18, y0 + 22, x0 + 26, y0 + 30, fill=ui.INK, outline="")
        c.create_text(x0 + 36, y0 + TOOL_H / 2, anchor="w", text=hint, fill=ui.TEXT, font=ui.font(11))
        ui.Button(c, x0 + tool_w - 188, y0 + 9, 84, 34, "Undo", self.undo, icon=ui.icon_undo)
        ui.Button(c, x0 + tool_w - 98, y0 + 9, 88, 34, "Done", self.close, icon=ui.icon_check,
                  fill=ui.BLUE, hover=ui.BLUE_HOVER, weight="bold")

        c.bind("<ButtonPress-1>", self._down)
        c.bind("<B1-Motion>", self._move)
        top.bind("<Escape>", lambda e: self.close())
        top.bind("<Control-z>", lambda e: self.undo())
        top.bind("<Command-z>", lambda e: self.undo())
        top.lift()
        top.focus_force()

    def _on_toolbar(self, x, y) -> bool:
        x0, y0, x1, y1 = self.tool_box
        return x0 <= x <= x1 and y0 <= y <= y1

    def _down(self, e):
        if self._on_toolbar(e.x, e.y):
            self.strokes.append(None)  # placeholder so _move ignores this press
            return
        self.strokes.append([(e.x, e.y)])
        self.items.append([self.canvas.create_oval(e.x - 3, e.y - 3, e.x + 3, e.y + 3, fill=ui.INK, outline="")])

    def _move(self, e):
        if not self.strokes or self.strokes[-1] is None:
            return
        x0, y0 = self.strokes[-1][-1]
        self.strokes[-1].append((e.x, e.y))
        self.items[-1].append(self.canvas.create_line(x0, y0, e.x, e.y, fill=ui.INK, width=5,
                                                      capstyle="round", smooth=True))

    def add_stroke(self, pts):
        """Draw a stroke programmatically (self-test)."""
        self._down(type("E", (), {"x": pts[0][0], "y": pts[0][1]}))
        for x, y in pts[1:]:
            self._move(type("E", (), {"x": x, "y": y}))

    def _real_strokes(self):
        return [s for s in self.strokes if s]

    def undo(self):
        while self.strokes and self.strokes[-1] is None:
            self.strokes.pop()
        if self.strokes:
            self.strokes.pop()
            for i in self.items.pop():
                self.canvas.delete(i)

    def marked_up(self) -> Image.Image | None:
        strokes = self._real_strokes()
        if not strokes:
            return None
        img = self.shot.copy()
        d = ImageDraw.Draw(img)
        w = max(4, round(5 * self.sx))
        for s in strokes:
            pts = [(round(x * self.sx), round(y * self.sy)) for x, y in s]
            if len(pts) == 1:
                x, y = pts[0]
                d.ellipse((x - w, y - w, x + w, y + w), fill=ui.INK)
            else:
                d.line(pts, fill=ui.INK, width=w, joint="curve")
        return img

    def close(self):
        img = self.marked_up()
        self.top.destroy()
        self.on_close(img)


class App:
    """The floating bar. States: recording -> processing -> done (or error), then it closes."""

    def __init__(self, rec: Recorder, on_stop):
        self.rec = rec
        self.on_stop = on_stop          # runs in a worker thread after Stop; returns the feedback path
        self.overlay: Overlay | None = None
        self.draw_started = 0.0
        self.state = "recording"
        self.result = None
        self.error: BaseException | None = None
        self._finished = threading.Event()
        self.snap_dir: Path | None = None

        root = self.root = tk.Tk()
        root.title("Site feedback")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        bg = ui.make_see_through(root)
        c = self.c = tk.Canvas(root, width=BAR_W, height=BAR_H, highlightthickness=0, bg=bg)
        c.pack()
        self.panel = ui.panel_image(BAR_W, BAR_H)
        c.create_image(0, 0, anchor="nw", image=self.panel, tags="panel")
        c.tag_bind("panel", "<ButtonPress-1>", self._grab)
        c.tag_bind("panel", "<B1-Motion>", self._drag)
        self._recording_view()

        root.update_idletasks()
        root.geometry(f"{BAR_W}x{BAR_H}+{root.winfo_screenwidth() - BAR_W - 28}+36")
        root.update()
        hide_from_capture(root)
        self._tick()

    # --- views -------------------------------------------------------------

    def _clear(self):
        self.c.delete("content")
        for b in getattr(self, "buttons", []):
            b.destroy()
        self.buttons = []

    def _recording_view(self):
        self._clear()
        c = self.c
        self.dot = c.create_oval(18, 21, 28, 31, fill=ui.RED, outline="", tags=("content", "panel"))
        self.clock = c.create_text(36, BAR_H / 2, anchor="w", text="0:00", fill=ui.TEXT,
                                   font=ui.font(12, "bold"), tags=("content", "panel"))
        c.create_line(96, 14, 96, BAR_H - 14, fill=ui.PANEL_EDGE, tags="content")
        self.buttons = [
            ui.Button(c, 106, 9, 88, 34, "Draw", self.open_draw, icon=ui.icon_pen),
            ui.Button(c, 200, 9, 82, 34, "Stop", self.stop, icon=ui.icon_stop),
        ]

    def _status_view(self, text: str, kind: str):
        self._clear()
        c = self.c
        if kind == "busy":
            self.spin = c.create_arc(16, 16, 36, 36, start=90, extent=270, style="arc", outline=ui.BLUE,
                                     width=3, tags="content")
            self._spin()
        elif kind == "done":
            c.create_oval(16, 16, 36, 36, fill=ui.GREEN, outline="", tags="content")
            ui.icon_check(c, 26, 26, "content")
        else:
            c.create_oval(16, 16, 36, 36, fill=ui.RED, outline="", tags="content")
            c.create_text(26, 26, text="!", fill=ui.TEXT, font=ui.font(12, "bold"), tags="content")
        c.create_text(48, BAR_H / 2, anchor="w", text=text, fill=ui.TEXT, font=ui.font(11),
                      tags=("content", "panel"))

    def _spin(self):
        if self.state != "processing":
            return
        self.c.itemconfig(self.spin, start=(float(self.c.itemcget(self.spin, "start")) - 24) % 360)
        self.root.after(50, self._spin)

    # --- behaviour ---------------------------------------------------------

    def _grab(self, e):
        self._off = (e.x, e.y)

    def _drag(self, e):
        x = self.root.winfo_pointerx() - self._off[0]
        y = self.root.winfo_pointery() - self._off[1]
        self.root.geometry(f"+{x}+{y}")

    def _bar_centre(self) -> tuple[int, int]:
        r = self.root
        return r.winfo_rootx() + BAR_W // 2, r.winfo_rooty() + BAR_H // 2

    def _tick(self):
        if self.state != "recording":
            return
        if not self.overlay:
            self.rec.point = self._bar_centre()
        t = int(self.rec.now())
        self.c.itemconfig(self.clock, text=f"{t // 60}:{t % 60:02d}")
        self.c.itemconfig(self.dot, fill=ui.RED if t % 2 == 0 else ui.RED_DIM)
        self.root.after(500, self._tick)

    def open_draw(self):
        if self.overlay or self.state != "recording":
            return
        self.rec.drawing.set()
        self.draw_started = self.rec.now()
        self.rec.point = self._bar_centre()
        self.root.withdraw()
        self.root.after(250, self._freeze)  # let the bar vanish before the screenshot

    def _freeze(self):
        with MSS() as sct:
            mon = monitor_at(sct, *self.rec.point)
            shot = grab(sct, mon)
        self.overlay = Overlay(self.root, shot, mon, self._drawn)

    def _drawn(self, img):
        if img is not None:
            self.rec.save_drawing(img, self.draw_started, self.rec.now())
        self.overlay = None
        self.rec.drawing.clear()
        self.root.deiconify()
        self.root.attributes("-topmost", True)

    def stop(self):
        if self.state != "recording":
            return
        if self.overlay:
            self.overlay.close()
        self.state = "processing"
        self._status_view("Got it. Sending to your agent…", "busy")
        threading.Thread(target=self._work, daemon=True).start()
        self.root.after(100, self._wait)

    def _work(self):
        try:
            self.result = self.on_stop()
        except BaseException as e:  # shown in the bar, re-raised by run()
            self.error = e
        self._finished.set()

    def _wait(self):
        if not self._finished.is_set():
            self.root.after(100, self._wait)
            return
        if self.error:
            self.state = "error"
            self._status_view("Something went wrong. Ask your agent.", "error")
            self.root.after(4000, self.root.quit)
        else:
            self.state = "done"
            self._status_view("Done. Your agent has it.", "done")
            self.root.after(1800, self.root.quit)
        self._snap("4-done")

    # --- self-test -----------------------------------------------------------

    def _snap(self, name):
        """Self-test only: save a picture of the bar (or the overlay) for review."""
        if not self.snap_dir:
            return
        self.root.update()
        with MSS() as sct:
            if self.overlay:
                t = self.overlay.top
                box = {"left": t.winfo_rootx(), "top": t.winfo_rooty(), "width": t.winfo_width(),
                       "height": t.winfo_height()}
            else:
                pad = 24
                box = {"left": self.root.winfo_rootx() - pad, "top": self.root.winfo_rooty() - pad,
                       "width": BAR_W + 2 * pad, "height": BAR_H + 2 * pad}
            grab(sct, box).save(self.snap_dir / f"selftest-{name}.png")

    def selftest(self, snap_dir: Path):
        """Scripted run: open the overlay, draw a circle, close it, stop. Saves pictures of each state."""
        self.snap_dir = snap_dir

        def draw():
            sw, sh = self.overlay.top.winfo_width(), self.overlay.top.winfo_height()
            cx, cy, r = sw // 2, sh // 2, min(sw, sh) // 8
            self.overlay.add_stroke([(cx + r * math.cos(a / 20), cy + r * math.sin(a / 20)) for a in range(0, 130)])
            self._snap("2-drawing")
        self.root.after(1200, lambda: self._snap("1-recording"))
        self.root.after(1500, self.open_draw)
        self.root.after(3000, draw)
        self.root.after(4000, lambda: self.overlay and self.overlay.close())
        self.root.after(9000, self.stop)
        self.root.after(9400, lambda: self._snap("3-processing"))

    def run(self):
        self.root.mainloop()
        self.root.destroy()
        if self.error:
            raise self.error
        return self.result
