"""Look and feel: a dark floating panel in the style of Apple's HUD controls
(the macOS screenshot toolbar, Markup), drawn on a Tk canvas so it looks the
same on Windows and macOS instead of using each platform's dated Tk buttons.
"""
from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont

from PIL import Image, ImageDraw, ImageTk

# Apple system colours, dark appearance.
PANEL = "#1c1c1e"
PANEL_EDGE = "#3a3a3c"
BUTTON = "#2c2c2e"
BUTTON_HOVER = "#3a3a3c"
TEXT = "#f5f5f7"
TEXT_DIM = "#98989d"
RED = "#ff453a"
RED_DIM = "#7a2520"
BLUE = "#0a84ff"
BLUE_HOVER = "#3d9bff"
GREEN = "#30d158"
INK = "#ff3b30"   # pen colour

# Pixels of this colour become see-through (Windows), giving the panel round corners.
KEY = "#010203"


def font(size: int, weight: str = "normal") -> tuple:
    families = set(tkfont.families())
    for fam in ("SF Pro Text", "SF Pro", "Segoe UI Variable Text", "Segoe UI", "Helvetica Neue", "Helvetica"):
        if fam in families:
            return (fam, size, weight)
    return ("TkDefaultFont", size, weight)


def make_see_through(win: tk.Misc) -> str:
    """Return the canvas background to use so everything outside the panel is invisible."""
    if sys.platform == "win32":
        win.configure(bg=KEY)
        win.attributes("-transparentcolor", KEY)
        return KEY
    if sys.platform == "darwin":
        win.configure(bg="systemTransparent")
        win.attributes("-transparent", True)
        return "systemTransparent"
    return PANEL


def panel_image(w: int, h: int, radius: int = 14, keyed: bool = True) -> ImageTk.PhotoImage:
    """Anti-aliased rounded panel with a hairline edge (drawn 4x and scaled down).

    keyed: the panel sits in a see-through window (the bar). False when it is drawn
    over a picture (the draw overlay), where real alpha blending is available.
    """
    s = 4
    big = Image.new("RGBA", (w * s, h * s), (1, 2, 3, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius * s, fill=PANEL_EDGE)
    d.rounded_rectangle((s, s, w * s - 1 - s, h * s - 1 - s), (radius - 1) * s, fill=PANEL)
    img = big.resize((w, h), Image.LANCZOS)
    if keyed and sys.platform == "win32":
        # Transparent-colour keying is all-or-nothing: flatten soft edges onto the key colour.
        flat = Image.new("RGB", (w, h), (1, 2, 3))
        alpha = img.getchannel("A").point(lambda a: 255 if a > 96 else 0)
        flat.paste(img.convert("RGB"), mask=alpha)
        return ImageTk.PhotoImage(flat)
    return ImageTk.PhotoImage(img)


def rounded_rect(c: tk.Canvas, x0, y0, x1, y1, r, **kw) -> int:
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


class Button:
    """Rounded-rectangle canvas button with an optional drawn icon and hover state."""

    def __init__(self, c: tk.Canvas, x: int, y: int, w: int, h: int, label: str, command,
                 icon=None, fill=BUTTON, hover=BUTTON_HOVER, fg=TEXT, weight="normal"):
        self.c, self.command, self.fill, self.hover = c, command, fill, hover
        self.tag = f"btn{id(self)}"
        rounded_rect(c, x, y, x + w, y + h, 9, fill=fill, outline="", tags=(self.tag, self.tag + "bg"))
        tx = x + w / 2
        if icon:
            icon(c, x + 18, y + h / 2, self.tag)
            tx = x + 18 + (w - 18) / 2 + 2
        c.create_text(tx, y + h / 2, text=label, fill=fg, font=font(11, weight), tags=self.tag)
        c.tag_bind(self.tag, "<Enter>", lambda e: (c.itemconfig(self.tag + "bg", fill=self.hover),
                                                   c.config(cursor="hand2")))
        c.tag_bind(self.tag, "<Leave>", lambda e: (c.itemconfig(self.tag + "bg", fill=self.fill),
                                                   c.config(cursor="")))
        c.tag_bind(self.tag, "<ButtonRelease-1>", lambda e: self.command())

    def destroy(self):
        self.c.delete(self.tag)


# Icons: drawn from primitives so no icon font or image files are needed.

def icon_pen(c, x, y, tag):
    c.create_line(x - 5, y + 5, x + 4, y - 4, fill=TEXT, width=3, capstyle="round", tags=tag)
    c.create_line(x - 6, y + 6, x - 5, y + 5, fill=INK, width=3, capstyle="round", tags=tag)


def icon_stop(c, x, y, tag):
    rounded_rect(c, x - 5, y - 5, x + 5, y + 5, 2, fill=RED, outline="", tags=tag)


def icon_undo(c, x, y, tag):
    c.create_arc(x - 6, y - 5, x + 6, y + 7, start=0, extent=200, style="arc", outline=TEXT, width=2, tags=tag)
    c.create_line(x - 7, y - 1, x - 6, y + 2, x - 3, y + 1, fill=TEXT, width=2, tags=tag)


def icon_check(c, x, y, tag):
    c.create_line(x - 5, y, x - 1, y + 4, x + 6, y - 4, fill=TEXT, width=2, capstyle="round",
                  joinstyle="round", tags=tag)
