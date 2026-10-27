"""The two windows the person sees: a small always-on-top bar, and the draw overlay.

Drawing works on a frozen screenshot shown full-screen, not on a transparent window.
That behaves the same on Windows and macOS (no click-through or transparency tricks),
and the marked-up image is exactly what was on screen.
"""
from __future__ import annotations

import math
import sys
import tkinter as tk

from PIL import Image, ImageDraw, ImageTk

from .capture import MSS, Recorder, grab, monitor_at

RED = "#ff2d2d"
BAR_BG = "#1b1b1f"
BAR_FG = "#f2f2f2"


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
    if sys.platform == "win32":
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
        c = self.canvas = tk.Canvas(top, width=sw, height=sh, highlightthickness=0, cursor="pencil", bg="black")
        c.pack(fill="both", expand=True)
        self.photo = ImageTk.PhotoImage(shot.resize((sw, sh)))
        c.create_image(0, 0, anchor="nw", image=self.photo)
        c.create_rectangle(3, 3, sw - 3, sh - 3, outline=RED, width=6)

        bar = tk.Frame(c, bg=BAR_BG, padx=10, pady=6)
        tk.Label(bar, text="Draw on the screen. Keep talking.", bg=BAR_BG, fg=BAR_FG,
                 font=("Helvetica", 14)).pack(side="left", padx=(0, 12))
        tk.Button(bar, text="Undo", command=self.undo, font=("Helvetica", 14)).pack(side="left", padx=4)
        tk.Button(bar, text="Done drawing", command=self.close, font=("Helvetica", 14, "bold")).pack(side="left", padx=4)
        c.create_window(sw // 2, 16, anchor="n", window=bar)

        c.bind("<ButtonPress-1>", self._down)
        c.bind("<B1-Motion>", self._move)
        top.bind("<Escape>", lambda e: self.close())
        top.bind("<Control-z>", lambda e: self.undo())
        top.bind("<Command-z>", lambda e: self.undo())
        top.lift()
        top.focus_force()

    def _down(self, e):
        self.strokes.append([(e.x, e.y)])
        self.items.append([self.canvas.create_oval(e.x - 3, e.y - 3, e.x + 3, e.y + 3, fill=RED, outline=RED)])

    def _move(self, e):
        if not self.strokes:
            return
        x0, y0 = self.strokes[-1][-1]
        self.strokes[-1].append((e.x, e.y))
        self.items[-1].append(self.canvas.create_line(x0, y0, e.x, e.y, fill=RED, width=5,
                                                      capstyle="round", smooth=True))

    def add_stroke(self, pts):
        """Draw a stroke programmatically (self-test)."""
        self._down(type("E", (), {"x": pts[0][0], "y": pts[0][1]}))
        for x, y in pts[1:]:
            self._move(type("E", (), {"x": x, "y": y}))

    def undo(self):
        if self.strokes:
            self.strokes.pop()
            for i in self.items.pop():
                self.canvas.delete(i)

    def marked_up(self) -> Image.Image | None:
        if not self.strokes:
            return None
        img = self.shot.copy()
        d = ImageDraw.Draw(img)
        w = max(4, round(5 * self.sx))
        for s in self.strokes:
            pts = [(round(x * self.sx), round(y * self.sy)) for x, y in s]
            if len(pts) == 1:
                x, y = pts[0]
                d.ellipse((x - w, y - w, x + w, y + w), fill=RED)
            else:
                d.line(pts, fill=RED, width=w, joint="curve")
        return img

    def close(self):
        img = self.marked_up()
        self.top.destroy()
        self.on_close(img)


class App:
    def __init__(self, rec: Recorder):
        self.rec = rec
        self.overlay: Overlay | None = None
        self.draw_started = 0.0

        root = self.root = tk.Tk()
        root.title("Site feedback")
        root.attributes("-topmost", True)
        root.resizable(False, False)
        root.configure(bg=BAR_BG)
        root.protocol("WM_DELETE_WINDOW", self.stop)

        f = tk.Frame(root, bg=BAR_BG, padx=12, pady=10)
        f.pack()
        self.clock = tk.Label(f, text="● REC 00:00", fg=RED, bg=BAR_BG, font=("Helvetica", 15, "bold"))
        self.clock.pack(side="left", padx=(0, 12))
        tk.Button(f, text="Draw", command=self.open_draw, font=("Helvetica", 15), width=6).pack(side="left", padx=4)
        tk.Button(f, text="Stop", command=self.stop, font=("Helvetica", 15), width=6).pack(side="left", padx=4)

        root.update_idletasks()
        root.geometry(f"+{root.winfo_screenwidth() - root.winfo_reqwidth() - 30}+40")
        root.update()
        hide_from_capture(root)
        self._tick()

    def _bar_centre(self) -> tuple[int, int]:
        r = self.root
        return r.winfo_rootx() + r.winfo_width() // 2, r.winfo_rooty() + r.winfo_height() // 2

    def _tick(self):
        if not self.overlay:
            self.rec.point = self._bar_centre()
        t = int(self.rec.now())
        self.clock.config(text=f"● REC {t // 60:02d}:{t % 60:02d}")
        self.root.after(500, self._tick)

    def open_draw(self):
        if self.overlay:
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
        if self.overlay:
            self.overlay.close()
        self.root.quit()

    def selftest(self):
        """Scripted run: open the overlay, draw a circle, close it, stop."""
        def draw():
            sw, sh = self.overlay.top.winfo_width(), self.overlay.top.winfo_height()
            cx, cy, r = sw // 2, sh // 2, min(sw, sh) // 8
            self.overlay.add_stroke([(cx + r * math.cos(a / 20), cy + r * math.sin(a / 20)) for a in range(0, 130)])
        self.root.after(1500, self.open_draw)
        self.root.after(3000, draw)
        self.root.after(4000, lambda: self.overlay and self.overlay.close())
        self.root.after(9000, self.stop)

    def run(self):
        self.root.mainloop()
        self.root.destroy()
