#!/usr/bin/env python3
"""Draws docs/demo.gif: a short terminal recording of Hats, generated rather than
screen-captured so it can be remade after changing how Hats looks.

    python3 -m pip install pillow     # only needed for this script, not for Hats itself
    python3 docs/make_demo.py

All names in it are examples. Colours match the palette in hat.py.
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
    sys.exit("Font %s not found; install the DejaVu fonts." % name)


# ------------------------------------------------------------------ look

SIZE = 18
REG, BOLD = font("DejaVuSansMono.ttf", SIZE), font("DejaVuSansMono-Bold.ttf", SIZE)
CAP_FONT, STEP_FONT = font("DejaVuSans-Bold.ttf", 19), font("DejaVuSans-Bold.ttf", 15)
NOTE_FONT, KEY_FONT = font("DejaVuSans-Bold.ttf", 15), font("DejaVuSansMono-Bold.ttf", 17)
CW = REG.getlength("M")
LH = 27
COLS, ROWS = 92, 15
PAD, TAB_H, CAP_H = 22, 38, 58
W = int(COLS * CW) + 2 * PAD
H = TAB_H + ROWS * LH + 2 * PAD + CAP_H

BG, TABBAR, FG = (37, 40, 42), (24, 26, 27), (211, 215, 207)
DIM, RULE = (138, 143, 140), (74, 79, 82)
CAPTION_BG, CAPTION_FG, STEP_BG = (16, 17, 18), (236, 238, 234), (95, 175, 255)
GREEN, BLUE, YELLOW, RED = (138, 226, 52), (114, 159, 207), (255, 215, 95), (255, 95, 95)
ACCOUNT = {"personal": (135, 215, 135), "work": (95, 175, 255), "client-a": (215, 135, 215)}

TYPE_MS, BLINK_MS, FADE_FRAMES = 55, 530, 5
FADE_MS, DIP = 35, 1.0   # ms per fade frame; how far a whole-screen change dims (1.0: to the background)


def ease(t):
    """Slow at the start and the end of a fade, so it looks smooth."""
    return t * t * (3 - 2 * t)

# A line is a list of segments: (text, colour, bold, highlighted). A highlighted
# segment gets an outline, to draw the eye to what just changed.


def seg(text, color=FG, bold=False, hl=False):
    return (text, color, bold, hl)


def prompt(account, path, pinned=False, hl=False):
    return [seg(account + (" · pinned" if pinned else ""), ACCOUNT[account], True, hl), seg(" "),
            seg("you@laptop", GREEN, True), seg(":"), seg(path, BLUE, True), seg("$ ")]


RULE_LINE = [seg("\x00rule")]


def note(text):
    """An explanation drawn after the line's text, in the caption colours, so it never
    looks like part of the terminal."""
    return seg("\x00note" + text)


class Film:
    """Collects frames: draws the screen, and handles typing, blinking and fades."""

    def __init__(self):
        self.lines, self.title, self.caption, self.step = [], "", "", ""
        self.cursor = True
        self.key = None      # a key shown as a badge while it is "pressed"
        self.frames = []

    def render(self, cursor_on=True):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, TAB_H], fill=TABBAR)
        d.rounded_rectangle([PAD - 10, 8, PAD + REG.getlength(self.title) + 26, TAB_H + 6], 6, fill=BG)
        d.text((PAD + 8, 15), self.title, font=REG, fill=FG)
        y = TAB_H + PAD
        lines = self.lines[-ROWS:]
        for n, line in enumerate(lines):
            x = PAD
            for text, color, bold, hl in line:
                if text == "\x00rule":
                    d.line([PAD, y + LH // 2, W - PAD, y + LH // 2], fill=RULE, width=1)
                    continue
                if text.startswith("\x00note"):
                    words = text[5:]
                    nx = x + (14 if x > PAD + CW * 8 else 0)
                    tw = NOTE_FONT.getlength(words)
                    d.rounded_rectangle([nx, y - 1, nx + tw + 16, y + LH - 5], 11, fill=STEP_BG)
                    d.text((nx + 8, y + 3), words, font=NOTE_FONT, fill=CAPTION_BG)
                    x = nx + tw + 16
                    continue
                f = BOLD if bold else REG
                width = f.getlength(text)
                if hl:
                    d.rounded_rectangle([x - 6, y - 3, x + width + 6, y + LH - 4], 6, outline=color, width=2)
                d.text((x, y), text, font=f, fill=color)
                x += width
            if self.cursor and cursor_on and n == len(lines) - 1:
                d.rectangle([x + 1, y + 2, x + CW - 1, y + LH - 5], fill=FG)
            y += LH
        top = H - CAP_H
        if self.key:
            kw = KEY_FONT.getlength(self.key) + 36
            kx, ky = W - PAD - kw, top - 58
            d.rounded_rectangle([kx, ky + 4, kx + kw, ky + 46], 9, fill=(14, 15, 16))
            d.rounded_rectangle([kx, ky, kx + kw, ky + 42], 9, fill=(68, 72, 76), outline=(150, 155, 152), width=2)
            d.text((kx + 18, ky + 10), self.key, font=KEY_FONT, fill=CAPTION_FG)
        d.rectangle([0, top, W, H], fill=CAPTION_BG)
        x = PAD
        if self.step:
            sw = STEP_FONT.getlength(self.step) + 18
            d.rounded_rectangle([x, top + 15, x + sw, top + 43], 14, fill=STEP_BG)
            d.text((x + 9, top + 20), self.step, font=STEP_FONT, fill=CAPTION_BG)
            x += sw + 14
        d.text((x, top + 17), self.caption, font=CAP_FONT, fill=CAPTION_FG)
        return img

    def add(self, img, ms):
        self.frames.append((img, ms))

    def hold(self, ms):
        """Show the screen for ms, with the cursor blinking."""
        on = True
        while ms > 0:
            t = min(BLINK_MS, ms)
            self.add(self.render(on), t)
            ms -= t
            on = not on

    def type(self, text, line=-1, color=FG):
        """Type into a line, one character per frame."""
        for ch in text:
            self.lines[line] = self.lines[line] + [seg(ch, color)]
            self.add(self.render(True), TYPE_MS)
        self.hold(350)

    def change(self, apply, whole=False):
        """Move to the screen apply() sets up. The tab title and caption switch at once
        (fading text over text reads as a blur). The terminal area either fades the new
        lines in, or, for a whole new screen (whole=True), dims to the background and
        brightens again, so two screens are never seen on top of each other."""
        before = self.render(True)
        apply()
        after = self.render(True)
        body = (0, TAB_H, W, H - CAP_H)
        blank = Image.new("RGB", (W, H), BG)

        def frame(a, b, t):
            img = after.copy()
            img.paste(Image.blend(a, b, t).crop(body), body[:2])
            return img

        if whole:
            for k in range(1, FADE_FRAMES + 1):
                self.add(frame(before, blank, DIP * ease(k / FADE_FRAMES)), FADE_MS)
            for k in range(1, FADE_FRAMES + 1):
                self.add(frame(blank, after, 1 - DIP * (1 - ease(k / FADE_FRAMES))), FADE_MS)
        else:
            for k in range(1, FADE_FRAMES + 1):
                self.add(frame(before, after, k / (FADE_FRAMES + 1)), 40)


# ------------------------------------------------------------------ what is shown

def limits(indent, parts, resets=True):
    """A second line under an account: what is left of its limits."""
    line = [seg(" " * indent)]
    for j, (label, left, reset) in enumerate(parts):
        col = RED if left <= 20 else YELLOW if left <= 50 else ACCOUNT["personal"]
        if j:
            line.append(seg(" · ", DIM))
        line += [seg(label + " ", DIM), seg("%d%% left" % left, col)]
        if resets:
            line.append(seg(" (resets %s)" % reset, DIM))
    return line


ACCOUNTS = [("personal", "you@example.com · Max 5x", [("5h", 92, "18:00"), ("week", 64, "Thu 02:00")]),
            ("work", "you@acme.example · Acme · Team", [("week", 81, "Mon 09:00")]),
            ("client-a", "you@client-a.example · Client A · Team", [("5h", 18, "16:30"), ("week", 47, "Fri 11:00")])]


def menu_lines(sel):
    out = []
    for k, (name, who, parts) in enumerate(ACCOUNTS):
        mark = seg("▸", FG, True) if k == sel else seg(" ")
        out.append([seg(" "), mark, seg(" %d " % (k + 1), DIM), seg("%-8s" % name, ACCOUNT[name], True),
                    seg("  " + who)])
        out.append(limits(15, parts))
    out.append([seg("   a  ", DIM), seg("auto", FG, True), seg("  follow the folder — here that means work")])
    return out


def status_lines():
    out = [[]]
    for k, (name, who, parts) in enumerate(ACCOUNTS):
        label = name + (" · pinned" if k == 0 else "")
        out.append([seg(" ▸ " if k == 0 else "   ", FG, True), seg("%-17s" % label, ACCOUNT[name], True),
                    seg("  " + who)])
        out.append(limits(22, parts))
    return out


def story():
    f = Film()

    # 1. The prompt shows the account.
    f.step, f.caption, f.title = "1/5", "Your prompt always shows which Claude account is active", "personal — ~"
    f.lines = [prompt("personal", "~", hl=True)]
    f.hold(2400)
    f.lines = [prompt("personal", "~")]
    f.type("cd ~/code/acme")

    # 2. A folder picks its account.
    def to_work():
        f.step, f.caption = "2/5", "Folders belong to accounts: in Acme's code you are on work"
        f.title = "work — ~/code/acme"
        f.lines.append(prompt("work", "~/code/acme", hl=True))
    f.change(to_work)
    f.hold(2600)
    f.lines[-1] = prompt("work", "~/code/acme")
    f.type("claude")

    # 3. Inside Claude Code.
    def to_claude():
        f.step, f.caption = "3/5", "Inside Claude Code, the status line shows the account too"
        f.cursor = False
        f.lines = [[], [seg("  Claude Code  ", FG, True), seg("~/code/acme", DIM)], [], RULE_LINE,
                   [seg("> ", FG, True)], RULE_LINE,
                   [seg("  "), seg("work", ACCOUNT["work"], True, True), seg("  Acme · Team  "), seg("│", DIM),
                    seg("  Opus 5.5 · high  "), seg("│", DIM), seg("  context", DIM), seg(" 4% · "),
                    seg("5h", DIM), seg(" 12% · "), seg("week", DIM), seg(" 19%")]]
    f.change(to_claude, whole=True)
    f.hold(1200)
    for ch in "fix the failing login test":
        f.lines[4] = f.lines[4] + [seg(ch)]
        f.add(f.render(), TYPE_MS)
    f.hold(2200)

    # 4. F2: pick by hand.
    def to_shell():
        f.step, f.caption, f.cursor = "4/5", "Press F2 (or type hat) to choose an account by hand", True
        f.lines = [prompt("work", "~/code/acme")]
    f.change(to_shell, whole=True)
    f.hold(1400)
    header = [[], [seg("  Claude account for this terminal", FG, True)],
              [seg("  ↑/↓ move · Enter select · 1-3 or a to jump · q cancel", DIM)], []]

    def open_menu():
        f.cursor = False
        f.lines = [prompt("work", "~/code/acme")] + header + menu_lines(1)
    f.change(open_menu)
    f.hold(1600)
    f.lines = [prompt("work", "~/code/acme")] + header + menu_lines(0)
    f.hold(1600)

    def pinned():
        f.caption = "Picked by hand: this terminal stays on personal in every folder"
        f.title, f.cursor = "personal (pinned) — ~/code/acme", True
        f.lines = [prompt("work", "~/code/acme"), [],
                   [seg("→ personal · pinned", ACCOUNT["personal"], True), seg("  you@example.com · Max 5x"),
                    seg("  (pinned in this terminal)", DIM)],
                   prompt("personal", "~/code/acme", pinned=True, hl=True)]
    f.change(pinned, whole=True)
    f.hold(2600)
    f.lines[-1] = prompt("personal", "~/code/acme", pinned=True)
    f.type("hat status")

    # 5. What is left of each account's limits.
    def to_status():
        f.step, f.caption = "5/5", "hat status: how much of each account's limits is left, and when they reset"
        f.cursor = False
        f.lines = f.lines + status_lines()
    f.change(to_status)
    f.hold(5500)

    def back_to_start():
        f.step, f.caption, f.title = "1/5", "Your prompt always shows which Claude account is active", "personal — ~"
        f.cursor = True
        f.lines = [prompt("personal", "~", hl=True)]
    f.change(back_to_start, whole=True)
    return f.frames


def save(frames, out):
    """Write the frames as a looping GIF."""
    # One shared palette for every frame keeps colours steady (no flicker between
    # frames). It is built from frames spread over the whole film, so every account
    # colour is in it.
    picks = frames[::max(1, len(frames) // 12)]
    sample = Image.new("RGB", (W, H * len(picks)))
    for k, (img, _) in enumerate(picks):
        sample.paste(img, (0, H * k))
    palette = sample.quantize(colors=192, method=Image.Quantize.MEDIANCUT)
    images = [img.quantize(palette=palette, dither=Image.Dither.NONE) for img, _ in frames]
    images[0].save(out, save_all=True, append_images=images[1:], duration=[ms for _, ms in frames],
                   loop=0, optimize=True, disposal=1)
    print("wrote %s (%d frames, %.1f s, %d KB)"
          % (out, len(frames), sum(ms for _, ms in frames) / 1000, os.path.getsize(out) // 1024))


def main():
    save(story(), OUT)


if __name__ == "__main__":
    main()
