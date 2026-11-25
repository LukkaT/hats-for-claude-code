#!/usr/bin/env python3
"""Draws docs/settings.gif: automatic switching from start to end. It shows the
settings screen, a chat reaching the level, and the same chat continuing on the
next account. Uses the look and the Film helper of make_demo.py.

    python3 -m pip install pillow     # only needed for this script, not for Hats itself
    python3 docs/make_settings_demo.py

All names in it are examples. Colours match the palette in hat.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_demo as md  # noqa: E402
from make_demo import ACCOUNT, DIM, FG, RULE_LINE, TYPE_MS, YELLOW, Film, prompt, save, seg  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.gif")
md.ROWS = 19                                             # the settings screen is taller than the demo's
md.H = md.TAB_H + md.ROWS * md.LH + 2 * md.PAD + md.CAP_H
ON = (135, 215, 135)
STEPS = 8
LEFT = {"personal": "58%", "work": "97%"}


def screen(switch=False, level=10, order=(), sel="switch", carry=None, hl=None):
    """The `hat settings` screen, as hat.py draws it. hl: the part to outline."""
    def mark(item):
        if item == carry:
            return seg(" ⇅ ", YELLOW, True)
        return seg(" ❯ ", FG, True) if item == sel else seg("   ")

    text = FG if switch else DIM
    out = [[seg(" Hats · Settings", FG, True), seg(" " * 35 + "esc close", DIM)], [],
           [mark("switch"), seg("Move to another account when one runs low     "),
            seg("[ on ]", ON, True, hl == "switch") if switch else seg("[ off ]", DIM, False, hl == "switch")]]
    value = "◂ %d%% ▸" % level if sel == "level" else "%d%%" % level
    out.append([mark("level"), seg("Runs low = less than  ", text), seg(value, text, True, hl == "level"),
                seg("  left of its 5-hour or weekly limit", text)])
    out += [[], [seg("   Take turns, top first".ljust(46), text), seg("left now", DIM)]]
    for n, name in enumerate(order, 1):
        out.append([mark(name), seg("  %d  " % n, text), seg(name.ljust(35), ACCOUNT[name] if switch else DIM, True,
                                                                hl == name), seg("   " + LEFT[name], text)])
    if not order:
        out.append([seg("        (none yet)", DIM)])
    out += [[], [seg("   Never switch to or from", text)]]
    for name in ("personal", "work", "client-a"):
        if name not in order:
            out.append([mark(name), seg("     "), seg(name, ACCOUNT[name] if switch else DIM, True, hl == name)])
    out.append([])
    if not switch:
        now = ["Now: nothing moves. claude uses this folder's account (or", "the one you pick), as always."]
    elif len(order) < 2:
        now = ["Now: nothing moves yet. Put at least two accounts under Take", "turns (enter picks one up, enter drops it)."]
    else:
        now = ["Now: claude starts on personal. When it has less than %d%%" % level, "left, it moves on to work."]
    out += [[seg("   "), seg(line, text, False, hl == "now")] for line in now]
    hint = ("↑↓ move it · enter drop · esc put it back" if carry
            else "space on/off · ←→ change · enter: pick up an account, ↑↓ move, enter drop")
    return out + [[], [seg(" " + hint, DIM)]]


def claude_screen(account, who, left, chat, hint=False):
    """Claude Code with its status line. hint: the part saying where the chat can move on."""
    line = [seg("  "), seg(account, ACCOUNT[account], True, not hint), seg("  " + who + "  "), seg("│", DIM),
            seg("  Opus 5.5  "), seg("│", DIM), seg("  5h", DIM), seg(" %d%% · " % (100 - left)), seg("week", DIM),
            seg(" 20%")]
    if hint:
        line += [seg("  "), seg("│", DIM), seg("  "), seg("/exit → continue on work", YELLOW, False, True)]
    return [[], [seg("  Claude Code  ", FG, True), seg("~/code", DIM)], []] + chat + [
        RULE_LINE, [seg("> ", FG, True)], RULE_LINE, line]


CHAT = [[seg("> ", DIM), seg("refactor the login module and keep the tests green")],
        [seg("● ", ON), seg("Split auth.py into session.py and tokens.py; 41 tests pass.")], []]


def story():
    f = Film()
    top = prompt("personal", "~/code") + [seg("hat settings")]

    def show(n, caption, **kw):
        def apply():
            f.step, f.caption, f.cursor = "%d/%d" % (n, STEPS), caption, False
            f.lines = [top, []] + screen(**kw)
        f.change(apply)

    # 1. Off.
    f.step, f.caption = "1/%d" % STEPS, "hat settings opens the settings. Automatic switching starts off"
    f.title, f.lines = "personal — ~/code", [prompt("personal", "~/code")]
    f.type("hat settings")
    show(1, "hat settings opens the settings. Automatic switching starts off", hl="switch")
    f.hold(3400)

    # 2. On.
    show(2, "Space turns it on. Until two accounts take turns, nothing moves", switch=True, hl="switch")
    f.hold(3400)

    # 3. The level.
    level = "←→: an account is low when less than this is left of its 5-hour OR weekly limit"
    show(3, level, switch=True, level=15, sel="level", hl="level")
    f.hold(1300)
    show(3, level, switch=True, level=10, sel="level", hl="level")
    f.hold(3000)

    # 4. Pick up personal and drop it under Take turns.
    pick = "Enter picks an account up, ↑↓ moves it, Enter drops it under Take turns"
    show(4, pick, switch=True, sel="personal")
    f.hold(1000)
    show(4, pick, switch=True, sel="personal", carry="personal")
    f.hold(1000)
    show(4, pick, switch=True, order=("personal",), sel="personal", carry="personal")
    f.hold(1200)
    show(4, pick, switch=True, order=("personal",), sel="personal")
    f.hold(1000)

    # 5. The same for work; client-a stays out.
    keep = "work too. client-a stays under Never switch: never switched to or from"
    show(5, keep, switch=True, order=("personal",), sel="work", carry="work")
    f.hold(1000)
    show(5, keep, switch=True, order=("personal", "work"), sel="work", carry="work")
    f.hold(1000)
    show(5, keep, switch=True, order=("personal", "work"), sel="work", hl="client-a")
    f.hold(3000)

    # 6. The Now line.
    show(6, "The Now line says in plain words what claude will do", switch=True, order=("personal", "work"),
         sel="work", hl="now")
    f.hold(4200)

    # 7. A chat on personal reaches the level.
    def to_chat():
        f.step, f.caption = "7/%d" % STEPS, "Later, in a chat: personal is low, and the status line says so"
        f.lines = claude_screen("personal", "you@example.com · Max 5x", 8, CHAT, hint=True)
    f.change(to_chat, whole=True)
    f.hold(2000)
    for ch in "/exit":
        f.lines[-3] = f.lines[-3] + [seg(ch)]
        f.add(f.render(), TYPE_MS * 2)
    f.hold(1200)

    def asked():
        f.caption, f.cursor = "After /exit Hats asks. Enter means yes; n stays on personal", True
        f.lines = [prompt("personal", "~/code") + [seg("claude")],
                   [seg("hat: 'personal' has 8% left of its 5-hour limit (resets Thu 18:00).", YELLOW)],
                   [seg("Continue this chat on 'work'? [Y/n] ")]]
    f.change(asked, whole=True)
    f.hold(2800)
    f.type("y")
    f.lines.append([seg("hat: continuing on 'work' …")])
    f.add(f.render(), 900)

    # 8. The same chat on work.
    def on_work():
        f.step, f.caption = "8/%d" % STEPS, "The same chat carries on, now on work: its status line shows it"
        f.cursor, f.title = False, "work — ~/code"
        f.lines = claude_screen("work", "Acme · Team", 97, CHAT)
    f.change(on_work, whole=True)
    f.hold(1000)
    for ch in "now update the README":
        f.lines[-3] = f.lines[-3] + [seg(ch)]
        f.add(f.render(), TYPE_MS)
    f.hold(4000)

    def back():
        f.step, f.caption = "1/%d" % STEPS, "hat settings opens the settings. Automatic switching starts off"
        f.cursor, f.title = True, "personal — ~/code"
        f.lines = [prompt("personal", "~/code")]
    f.change(back, whole=True)
    return f.frames


if __name__ == "__main__":
    save(story(), OUT)
