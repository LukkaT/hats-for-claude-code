#!/usr/bin/env python3
"""Draws docs/demo.gif: a short terminal recording of Hats, generated rather than
screen-captured so it can be remade after changing how Hats looks.

    python3 -m pip install pillow     # only needed for this script, not for Hats itself
    python3 docs/make_demo.py

All names in it are examples. Colours match the palette (256-colour codes in hat.py).
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "demo.gif")

FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "C:/Windows/Fonts"]


def font(name, size):
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    sys.exit("Font %s not found; install DejaVu fonts." % name)


SIZE = 16
REG, BOLD = font("DejaVuSansMono.ttf", SIZE), font("DejaVuSansMono-Bold.ttf", SIZE)
CW = REG.getlength("M")                # character width
LH = 24                                # line height
COLS, ROWS = 96, 14
PAD = 18
TAB_H = 34
CAP_H = 46
W = int(COLS * CW) + 2 * PAD
H = TAB_H + ROWS * LH + 2 * PAD + CAP_H

# Colours: terminal theme, and the per-account colours (xterm-256 114, 75, 176, 246, 221).
BG, TABBAR, TAB, FG = (37, 40, 42), (27, 29, 31), (37, 40, 42), (211, 215, 207)
DIM, RULE, CAPTION_BG, CAPTION_FG = (138, 143, 140), (74, 79, 82), (18, 19, 20), (230, 232, 228)
GREEN, BLUE = (138, 226, 52), (114, 159, 207)
ACCOUNT = {"personal": (135, 215, 135), "work": (95, 175, 255), "client-a": (215, 135, 215)}
GREY, YELLOW = (148, 148, 148), (255, 215, 95)


def prompt(account, path, pinned=False):
    label = account + (" · pinned" if pinned else "")
    return [(label, ACCOUNT[account], True), (" ", FG, False), ("you@laptop", GREEN, True),
            (":", FG, False), (path, BLUE, True), ("$ ", FG, False)]


def plain(text, color=FG, bold=False):
    return [(text, color, bold)]


class Screen:
    """A terminal screen: lines of coloured segments, a tab title and a caption."""

    def __init__(self):
        self.lines, self.title, self.caption, self.frames = [], "", "", []

    def show(self, ms):
        self.frames.append((self.render(), ms))

    def render(self):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, TAB_H], fill=TABBAR)
        tab_w = min(W - 2 * PAD, int(REG.getlength(self.title)) + 36)
        d.rectangle([PAD - 8, 6, PAD - 8 + tab_w, TAB_H], fill=TAB)
        d.text((PAD + 10, 12), self.title, font=REG, fill=FG)
        y = TAB_H + PAD
        for line in self.lines[-ROWS:]:
            x = PAD
            for text, color, bold in line:
                if text == "\x00rule":
                    d.line([PAD, y + LH // 2, W - PAD, y + LH // 2], fill=RULE, width=1)
                    continue
                f = BOLD if bold else REG
                d.text((x, y), text, font=f, fill=color)
                x += f.getlength(text)
            y += LH
        d.rectangle([0, H - CAP_H, W, H], fill=CAPTION_BG)
        d.text((PAD, H - CAP_H + 13), self.caption, font=BOLD, fill=CAPTION_FG)
        return img

    def type(self, text, color=FG):
        """Type into the last line, a few characters per frame."""
        for i in range(0, len(text), 3):
            self.lines[-1] = self.lines[-1] + [(text[i:i + 3], color, False)]
            self.show(70)


def scenes():
    s = Screen()

    s.caption = "Your prompt always shows which Claude account `claude` will use"
    s.title = "personal — ~"
    s.lines = [prompt("personal", "~")]
    s.show(1600)
    s.type("cd ~/code/acme-app")
    s.show(300)

    s.caption = "Folders belong to accounts: cd into Acme's code and you are on the work account"
    s.title = "work — ~/code/acme-app"
    s.lines.append(prompt("work", "~/code/acme-app"))
    s.show(2200)
    s.type("claude")
    s.show(400)

    s.caption = "Inside Claude Code, the status line shows the account, team and usage"
    s.title = "work — ~/code/acme-app"
    s.lines = [[], plain("  Claude Code is running in ~/code/acme-app", DIM), [],
               [("\x00rule", RULE, False)], plain("> ", FG, True), [("\x00rule", RULE, False)],
               [("  work", ACCOUNT["work"], True), ("  Acme · Team  ", FG, False), ("│", DIM, False),
                ("  Opus 5.5 · high  ", FG, False), ("│", DIM, False), ("  context", DIM, False),
                (" 4% · ", FG, False), ("5h", DIM, False), (" 12% · ", FG, False),
                ("week", DIM, False), (" 31%", FG, False)]]
    s.show(400)
    s.lines[4] = plain("> ", FG, True)
    for chunk in ["fix the ", "failing ", "login test"]:
        s.lines[4] = s.lines[4] + [(chunk, FG, False)]
        s.show(160)
    s.show(2600)

    s.caption = "Press F2 (or type hat) to pick an account by hand for this terminal"
    s.lines = [prompt("work", "~/code/acme-app")]
    s.show(900)
    s.lines += [[], plain("  Claude account for this terminal", FG, True),
                plain("  ↑/↓ move · Enter select · 1-3 or a to jump · q cancel", DIM), []]
    rows = [("personal", "you@example.com · Max 5x"), ("work", "you@acme.example · Acme · Team"),
            ("client-a", "you@client-a.example · Client A · Team")]

    def menu(sel):
        out = []
        for k, (name, who) in enumerate(rows):
            mark = ("▸", FG, True) if k == sel else (" ", FG, False)
            out.append([(" ", FG, False), mark, (" %d " % (k + 1), DIM, False),
                        ("%-9s" % name, ACCOUNT[name], True), ("  " + who, FG, False)])
        out.append([("   a  ", DIM, False), ("auto", FG, True),
                    ("  follow the folder — here that means work", FG, False)])
        return out

    base = list(s.lines)
    for sel, ms in ((1, 1300), (0, 1100)):
        s.lines = base + menu(sel)
        s.show(ms)
    s.lines = base + menu(0) + [[],
                                [("→ personal · pinned", ACCOUNT["personal"], True),
                                 ("  you@example.com · Max 5x  ", FG, False),
                                 ("(pinned in this terminal)", DIM, False)],
                                prompt("personal", "~/code/acme-app", pinned=True)]
    s.title = "personal (pinned) — ~/code/acme-app"
    s.caption = "Pinned: this terminal stays on personal in every folder, until `hat auto`"
    s.show(3600)
    return s.frames


def main():
    frames = scenes()
    images = [f.convert("P", palette=Image.ADAPTIVE, colors=64) for f, _ in frames]
    images[0].save(OUT, save_all=True, append_images=images[1:], duration=[ms for _, ms in frames],
                   loop=0, optimize=True, disposal=1)
    print("wrote %s (%d frames, %d KB)" % (OUT, len(frames), os.path.getsize(OUT) // 1024))


if __name__ == "__main__":
    main()
