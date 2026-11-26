#!/usr/bin/env python3
"""Draws docs/settings.gif: automatic switching from start to end. It shows the
settings screen, a chat getting low, and the same chat continuing on the next
account. Every key press shows as a badge, and a short blue note says what changed.
Uses the look and the Film helper of make_demo.py.

    python3 -m pip install pillow     # only needed for this script, not for Hats itself
    python3 docs/make_settings_demo.py

All names in it are examples. Colours match the palette in hat.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_demo as md  # noqa: E402
from make_demo import ACCOUNT, DIM, FG, RULE_LINE, YELLOW, Film, note, prompt, save, seg  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "settings.gif")
STILLS = os.path.join(HERE, "settings")     # step-1.png ... : the step-by-step pictures in settings.md
md.ROWS = 19                                             # the settings screen is taller than the demo's
md.H = md.TAB_H + md.ROWS * md.LH + 2 * md.PAD + md.CAP_H
md.TYPE_MS = 38
md.FADE_FRAMES = 3                                       # a short, smooth dip between screens
ON = (135, 215, 135)
STEPS = 8
LEFT = {"personal": "58%", "work": "97%"}


def screen(switch=False, level=10, order=(), sel="switch", carry=None, notes=None):
    """The `hat settings` screen, as hat.py draws it. notes: {part: explanation}, where a
    part is "switch", "low" (under the level), an account, or "now"."""
    notes = notes or {}

    def mark(item):
        if item == carry:
            return seg(" ⇅ ", YELLOW, True)
        return seg(" ❯ ", FG, True) if item == sel else seg("   ")

    def explained(line, part):
        return line + [note(notes[part])] if part in notes else line

    text = FG if switch else DIM
    out = [[seg(" Hats · Settings", FG, True), seg(" " * 35 + "esc close", DIM)], []]
    out.append(explained([mark("switch"), seg("Move to another account when one runs low     "),
                          seg("[ on ]", ON, True) if switch else seg("[ off ]", DIM)], "switch"))
    value = "◂ %d%% ▸" % level if sel == "level" else "%d%%" % level
    out.append([mark("level"), seg("Runs low = less than  ", text), seg(value, text, True),
                seg("  left of its 5-hour or weekly limit", text)])
    out.append(explained([seg(" " * 23)], "low") if "low" in notes else [])
    out.append([seg("   Take turns, top first".ljust(46), text), seg("left now", DIM)])
    for n, name in enumerate(order, 1):
        out.append(explained([mark(name), seg("  %d  " % n, text), seg(name.ljust(12), ACCOUNT[name], True),
                              seg(" " * 26 + LEFT[name], text)], name))
    if not order:
        out.append([seg("        (none yet)", DIM)])
    out += [[], [seg("   Never switch to or from", text)]]
    for name in ("personal", "work", "client-a"):
        if name not in order:
            out.append(explained([mark(name), seg("     "), seg(name, ACCOUNT[name] if switch else DIM, True)], name))
    out.append([])
    if not switch:
        now = ["Now: nothing moves. claude uses this folder's account (or", "the one you pick), as always."]
    elif len(order) < 2:
        now = ["Now: nothing moves yet. Put at least two accounts under Take", "turns (enter picks one up, enter drops it)."]
    else:
        now = ["Now: claude starts on personal. When it has less than %d%%" % level, "left, it moves on to work."]
    out += [[seg("   "), seg(line, text)] for line in now]
    out.append(explained([seg(" " * 3)], "now") if "now" in notes else [])
    hint = ("↑↓ move it · enter drop · esc put it back" if carry
            else "space on/off · ←→ change · enter: pick up an account, ↑↓ move, enter drop")
    return out + [[seg(" " + hint, DIM)]]


def claude_screen(account, who, left, chat, low=False, say=None):
    """Claude Code with its status line. low: the status line says the chat will move.
    say: a note on the empty prompt line, pointing at the status line below."""
    line = [seg("  "), seg(account, ACCOUNT[account], True), seg("  " + who + "  "), seg("│", DIM),
            seg("  5h", DIM), seg(" %d%% · " % (100 - left)), seg("week", DIM), seg(" 20%")]
    if low:
        line += [seg("  "), seg("│", DIM), seg("  "), seg("low: moves to work after this task", YELLOW)]
    ask = [seg("> ", FG, True)] + ([seg(" " * 30), note(say)] if say else [])
    return [[], [seg("  Claude Code  ", FG, True), seg("~/code", DIM)], []] + chat + [RULE_LINE, ask, RULE_LINE, line]


ASKED = [seg("> ", DIM), seg("refactor the login module and keep the tests green")]
DONE = [seg("● ", ON), seg("Split auth.py into session.py and tokens.py; 41 tests pass.")]


def story():
    f = Film()
    top = prompt("personal", "~/code") + [seg("hat settings")]
    state = {}

    def show(n, caption, ms, key=None, snap=None, **kw):
        """Change the screen as if `key` was pressed, and hold it for ms. The change dims
        the screen briefly and brings the new one up (lines that move would ghost in a
        cross-fade). snap: save this moment as step picture number `snap`."""
        state.update(kw)

        def apply():
            f.step, f.caption, f.cursor, f.key = "%d/%d" % (n, STEPS), caption, False, key
            f.lines = [top, []] + screen(**state)
        f.change(apply, whole=True)
        if snap:
            still(snap)
        f.hold(ms)
        f.key = None

    def still(n):
        """The screen as it is now, without the caption bar, for the step-by-step guide."""
        os.makedirs(STILLS, exist_ok=True)
        img = f.render(False)
        img.crop((0, 0, md.W, md.H - md.CAP_H)).save(os.path.join(STILLS, "step-%d.png" % n), optimize=True)

    # 1. Open it: off.
    f.step, f.caption, f.key = "1/%d" % STEPS, "Open the settings", None
    f.title, f.lines = "personal — ~/code", [prompt("personal", "~/code")]
    f.type("hat settings")
    show(1, "Open the settings", 1700, key="ENTER", snap=1, notes={"switch": "◀ off: nothing ever moves"})

    # 2. On.
    show(2, "Turn it on", 1700, key="SPACE", snap=2, switch=True, notes={"switch": "◀ now on"})

    # 3. The level.
    show(3, "Choose when an account counts as low", 500, key="↓", sel="level", notes={})
    show(3, "Choose when an account counts as low", 2200, key="→", snap=3, level=15,
         notes={"low": "▲ low = less than 15% left of the 5-hour OR the weekly limit"})

    # 4. personal takes turns.
    pick = "Choose who takes turns: pick up, move, put down"
    show(4, pick, 600, key="↓", sel="personal", notes={})
    show(4, pick, 700, key="ENTER", carry="personal", notes={"personal": "◀ picked up"})
    show(4, pick, 700, key="↑", snap=4, order=("personal",), notes={"personal": "◀ moved into Take turns"})
    show(4, pick, 900, key="ENTER", carry=None, notes={"personal": "◀ 1st to work"})

    # 5. work too; client-a stays out.
    show(5, "work takes turns too", 500, key="↓", sel="work", notes={})
    show(5, "work takes turns too", 500, key="ENTER", carry="work", notes={"work": "◀ picked up"})
    show(5, "work takes turns too", 800, key="ENTER", order=("personal", "work"), carry=None,
         notes={"work": "◀ 2nd: takes over when personal is low"})
    show(5, "client-a stays out", 2200, snap=5, notes={"client-a": "◀ never switched to or from"})

    # 6. The Now line.
    show(6, "The Now line says what will happen", 2300, snap=6, notes={"now": "▲ always says it in plain words"})

    # 7. A chat on personal gets low; when the task is done, the chat moves by itself.
    def to_chat():
        f.step, f.caption, f.key = "7/%d" % STEPS, "Later, in a chat: personal gets low", None
        f.lines = claude_screen("personal", "Max 5x", 8,
                                [ASKED, [seg("● ", ON), seg("Running the tests…", DIM)], []],
                                low=True, say="▼ low now: it moves when this task is done")
    f.change(to_chat, whole=True)
    still(7)
    f.hold(2100)

    def task_done():
        f.caption = "The task is done"
        f.lines = claude_screen("personal", "Max 5x", 8, [ASKED, DONE, []], low=True)
    f.change(task_done, whole=True)
    f.hold(1000)

    def moving():
        f.caption = "So Hats moves the chat by itself: no /exit, no question"
        f.lines = [[], [seg("  Claude Code  ", FG, True), seg("~/code", DIM)], [], ASKED, DONE, [],
                   [seg("hat: 'personal' has 8% left of its 5-hour limit → this chat continues on 'work' …", YELLOW)],
                   [seg("    "), note("▲ automatic: no key pressed")]]
    f.change(moving, whole=True)
    still(8)
    f.hold(2200)

    # 8. The same chat on work.
    def on_work():
        f.step, f.caption = "8/%d" % STEPS, "Same chat, now on work: you just keep going"
        f.title = "work — ~/code"
        f.lines = claude_screen("work", "Acme · Team", 97, [ASKED, DONE, []], say="▼ same chat, now on work")
    f.change(on_work, whole=True)
    still(9)
    f.hold(1200)
    f.lines[-3] = [seg("> ", FG, True)]
    for ch in "now update the README":
        f.lines[-3] = f.lines[-3] + [seg(ch)]
        f.add(f.render(), md.TYPE_MS)
    f.hold(1500)

    def back():
        f.step, f.caption, f.key = "1/%d" % STEPS, "Open the settings", None
        f.cursor, f.title = True, "personal — ~/code"
        f.lines = [prompt("personal", "~/code")]
    f.change(back, whole=True)
    return f.frames


if __name__ == "__main__":
    save(story(), OUT)
