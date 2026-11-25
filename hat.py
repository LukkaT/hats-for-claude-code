#!/usr/bin/env python3
"""Hats for Claude Code: wear the right Claude account for every project.

Use several Claude accounts on one machine. Each account is a *profile*: its own
Claude Code config folder (CLAUDE_CONFIG_DIR) and therefore its own login. The
shell shows which profile is active (the name in its colour at the start of the
prompt, the tab title, and Claude Code's status line); you pick one from a menu
or let the folder decide.

Settings, history and memory stay shared: a profile folder links those back to
~/.claude, so only the login differs between profiles.

This file holds all the logic and runs on Linux, macOS and Windows with Python
3.8+ (standard library only). The shell files (hat.bash, hat.zsh, hat.ps1) are
thin hooks that call it.

Usage from a hook:  python3 hat.py [--shell bash|zsh|pwsh] [--eval] <command> [args]

With --eval, stdout carries only shell code for the hook to run (to change the
terminal's environment) and everything meant for people goes to stderr.
"""

import json
import os
import re
import sys
import time

VERSION = "1.0.0"
HOME = os.path.expanduser("~")
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
CONF_DIR = os.environ.get("HAT_HOME") or os.path.join(HOME, ".config", "hats")
CONF = os.path.join(CONF_DIR, "hats.conf")
BASE = os.path.join(HOME, ".claude")  # the standard Claude Code config folder; see Config.base
PROFILES_DIR = os.path.join(HOME, ".claude-profiles")

PALETTE = [114, 75, 176, 215, 80, 221]  # 256-colour codes, one per profile in config order
GREY, RED, YELLOW, DIMGREY = 246, 203, 221, 250
STYLES = ("clean", "badge", "minimal")

# Shared with ~/.claude through links. Not shared on purpose: .credentials.json and
# .claude.json (the login itself), plugins/ and skills/ (synced per account), caches.
SHARED_DIRS = ["projects", "file-history", "plans", "tasks", "todos", "paste-cache",
               "session-env", "commands", "agents"]
SHARED_FILES = ["settings.json", "CLAUDE.md", "keybindings.json", "history.jsonl"]
# What a "separate" profile keeps to itself: everything about past work.
# Its settings, CLAUDE.md, commands and agents are still shared.
WORK_DATA = {"projects", "file-history", "plans", "tasks", "todos", "paste-cache",
             "session-env", "history.jsonl"}
WARN_AT = 90  # % of a usage limit at which `claude` shows a warning

# Editors whose Claude extension can run on a profile: command, extensions folder.
EDITORS = {"code": ("code", "~/.vscode/extensions"),
           "cursor": ("cursor", "~/.cursor/extensions"),
           "windsurf": ("windsurf", "~/.windsurf/extensions")}

STARTER = """\
# Hats for Claude Code.   Edit by hand or with: hat add / remove / map / default / style
#
# default <profile>                           used when no "dir" rule matches
# style   <clean|badge|minimal>               how the prompt shows the account
# profile <name> <config-dir|native> [email]  "native" = the standard ~/.claude
# dir     <profile> <directory>               longest matching directory wins
# separate <profile>                          keeps its history and memory to itself
# base    <directory>                         what profiles share; ~/.claude when not set

default personal
style clean
"""


def starter():
    """The first config. Someone who already points CLAUDE_CONFIG_DIR at their own
    folder keeps it: that folder becomes the profile "personal" and what others share."""
    own = os.environ.get("CLAUDE_CONFIG_DIR", "")
    if own and not os.environ.get("HAT_PIN") and not inside(own, PROFILES_DIR):
        return STARTER + "base %s\nprofile personal %s\n" % (own, own)
    return STARTER + "profile personal native\n"

HELP = """\
Hats for Claude Code: a separate login per account, always visible.

The account name at the start of the prompt is the account `claude` uses here.
In its colour: signed in.  Grey: not signed in.  ⚠ in red: wrong account.

  claude                     starts Claude on that account
  hat   (or press F2)        menu: pick the account for this terminal
  hat status                 all profiles, their usage, and the folder rules
  hat use <profile>          pin this terminal to a profile without the menu
  hat auto                   unpin: follow the folder again
  hat add <name> [email] [--separate]   create a profile for another account
                             (--separate: its history and memory are not shared)
  hat login <profile>        sign a profile in (opens the browser)
  hat remove <profile>       sign a profile out and delete it
  hat map <profile> [dir]    always use <profile> in dir (default: current dir)
  hat unmap [dir]            remove that rule
  hat default <profile>      profile for folders without a rule
  hat style <clean|badge|minimal>  how the prompt shows the account
  hat run <profile> [args]   one-off: run claude with a profile
  hat exec <profile> <cmd>   run any command with a profile
  hat code <profile> [dir] [--editor code|cursor|windsurf]
                             open an editor whose Claude extension uses the profile
  hat doctor [--fix]         check the setup; --fix repairs broken links
  hat update                 get the latest version and reinstall
  hat export [file]          save profiles and folder rules (no logins) to a file
  hat import <file>          add them on this computer
  hat status --json          the same as status, for scripts
  hat edit                   open the config file
  hat version
"""


class Fail(Exception):
    """A message for the person; the command exits with status 2."""


# ------------------------------------------------------------------ output

class Out:
    """Where messages go and how escape codes are wrapped for the current shell."""
    stream = sys.stdout   # becomes stderr in --eval mode, where stdout carries shell code
    shell = "bash"


def say(text=""):
    Out.stream.write(text + "\n")
    Out.stream.flush()


def sgr(code):
    return "\x1b[" + code + "m"


def hide(seq, wrap=True):
    """Wrap a zero-width escape sequence so the shell's line editor does not count
    it as text. Only prompts need this; pass wrap=False everywhere else."""
    if not wrap:
        return seq
    if Out.shell == "bash":
        return "\x01" + seq + "\x02"
    if Out.shell == "zsh":
        return "%{" + seq + "%}"
    return seq


def plain_len(s):
    return len(re.sub(r"\x1b\[[0-9;]*m", "", s))


def enable_vt():
    """Let the Windows console draw colours and move the cursor."""
    if not IS_WIN:
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        for std in (-11, -12):  # stdout, stderr
            h = k.GetStdHandle(std)
            mode = ctypes.c_uint32()
            if k.GetConsoleMode(h, ctypes.byref(mode)):
                k.SetConsoleMode(h, mode.value | 0x0004)
    except Exception:
        pass


# ------------------------------------------------------------------ paths

def expand(p):
    return os.path.expanduser(p) if p.startswith("~") else p


def norm(p):
    """Comparable form of a path: real, absolute, case-folded where the OS is."""
    try:
        p = os.path.realpath(p)
    except OSError:
        p = os.path.abspath(p)
    return os.path.normcase(p.rstrip("/\\") or p)


def inside(child, parent):
    c, p = norm(child), norm(parent)
    return c == p or c.startswith(p.rstrip(os.sep) + os.sep)


def tilde(p):
    return "~" + p[len(HOME):] if p == HOME or p.startswith(HOME + os.sep) else p


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_atomic(path, text):
    """Replace a file's contents in one step. A file that is a symlink stays one."""
    path = os.path.realpath(path)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


# ------------------------------------------------------------------ config

class Config:
    """The parsed ~/.config/hats/hats.conf."""

    def __init__(self):
        if not os.path.exists(CONF):
            os.makedirs(CONF_DIR, exist_ok=True)
            write_atomic(CONF, starter())
        self.names = []        # profile names in file order (sets their colours)
        self.pdir = {}         # name -> config folder, or "native" for ~/.claude
        self.pmail = {}        # name -> expected login email ("" = any)
        self.rules = []        # (profile, folder)
        self.separate = set()  # profiles that keep their history and memory to themselves
        self.default, self.style, self.base = "", "clean", BASE
        with open(CONF, encoding="utf-8") as f:
            for line in f:
                parts = line.split(None, 2)
                if len(parts) < 2 or parts[0].startswith("#"):
                    continue
                kind, name = parts[0], parts[1]
                rest = parts[2].strip() if len(parts) > 2 else ""
                if kind == "default":
                    self.default = name
                elif kind == "style":
                    self.style = name
                elif kind == "base":
                    self.base = expand((name + " " + rest).strip())
                elif kind == "profile" and rest:
                    # The folder may contain spaces; an email, if any, is the last word.
                    folder, email = rest, ""
                    bits = rest.rsplit(None, 1)
                    if len(bits) == 2 and "@" in bits[1]:
                        folder, email = bits
                    self.names.append(name)
                    self.pdir[name] = "native" if folder == "native" else expand(folder)
                    self.pmail[name] = email
                elif kind == "dir" and rest:
                    self.rules.append((name, expand(rest)))
                elif kind == "separate":
                    self.separate.add(name)
        if self.default not in self.pdir and self.names:
            self.default = self.names[0]

    def dir(self, p):
        if p not in self.pdir:
            raise Fail("hat: unknown profile '%s' — known: %s" % (p, " ".join(self.names)))
        return self.pdir[p]

    def auto(self):
        """The profile the current folder asks for, and why."""
        cur, why, best = self.default, "default account", -1
        for p, d in self.rules:
            if inside(os.getcwd(), d) and len(norm(d)) >= best:
                cur, why, best = p, "folder rule " + tilde(d), len(norm(d))
        return cur, why

    def resolve(self, pin=None):
        """The profile in effect: a pin wins over the folder."""
        pin = os.environ.get("HAT_PIN", "") if pin is None else pin
        return (pin, "pinned in this terminal") if pin else self.auto()

    def managed(self, p):
        """True when Hats owns the profile's folder (~/.claude-profiles/<name>)."""
        d = self.pdir.get(p, "native")
        return d != "native" and inside(d, PROFILES_DIR)

    def links(self, p):
        """Create or repair the profile's links, if Hats manages its folder."""
        if self.managed(p):
            ensure_links(self.pdir[p], self.base, p in self.separate)

    def color(self, p):
        return PALETTE[self.names.index(p) % len(PALETTE)] if p in self.names else DIMGREY

    def profile_for_dir(self, d):
        """Which profile owns a CLAUDE_CONFIG_DIR value ("native" when unset)."""
        for p in self.names:
            pd = self.pdir[p]
            if (pd == "native") == (d == "native") and (pd == "native" or norm(pd) == norm(d)):
                return p
        return ""


def edit_conf(drop=lambda bits: False, set_key=None, add=None):
    """Rewrite hats.conf: drop lines for which drop(words) is true, set a one-word
    key ("default", "style") to a value, and append a line."""
    with open(CONF, encoding="utf-8") as f:
        lines = f.readlines()
    out, found = [], False
    for line in lines:
        bits = line.split(None, 2)
        if bits and set_key and bits[0] == set_key[0]:
            if not found:
                out.append("%s %s\n" % set_key)
            found = True
        elif not (bits and drop(bits)):
            out.append(line)
    if set_key and not found:
        out.append("%s %s\n" % set_key)
    if add:
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        out.append(add + "\n")
    write_atomic(CONF, "".join(out))


def is_rule_for(folder):
    return lambda bits: bits[0] == "dir" and len(bits) > 2 and norm(expand(bits[2].strip())) == norm(folder)


# ------------------------------------------------------------------ profile folders

def same(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def is_link(p):
    """A symlink, or on Windows any reparse point (junctions included). Python before
    3.12 reports a junction as a plain folder, and deleting "inside" it would delete
    the shared data it points to."""
    if os.path.islink(p):
        return True
    if IS_WIN:
        try:
            return bool(os.lstat(p).st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
        except (OSError, AttributeError):
            return False
    return False


def unlink(p):
    """Remove a link (symlink, junction or hard link) without touching what it points to."""
    if IS_WIN and os.path.isdir(p):
        os.rmdir(p)  # directory symlinks and junctions on Windows
    else:
        os.remove(p)


def remove_file(p):
    try:
        os.remove(p)
    except PermissionError:
        if not IS_WIN:
            raise
        import stat
        os.chmod(p, stat.S_IWRITE)  # read-only files, e.g. git objects in plugins/
        os.remove(p)


def link_dir(target, link):
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        if not IS_WIN:
            raise
        import _winapi  # a junction needs no admin rights or Developer Mode
        _winapi.CreateJunction(target, link)


def link_file(target, link):
    try:
        os.symlink(target, link)
    except OSError:
        if not IS_WIN:
            raise
        try:
            os.link(target, link)  # hard link: no admin rights needed, same drive only
        except OSError:
            pass  # cannot share this file; the profile keeps its own copy


def ensure_links(p, base=BASE, separate=False):
    """Make a profile folder share everything except the login with the base folder
    (~/.claude). Runs before every launch, so it also repairs a link that a write
    replaced. Only for folders Hats manages: ~/.claude-profiles/<name>.
    A separate profile does not share WORK_DATA; links to it are taken out."""
    if norm(p) == norm(base):
        return
    os.makedirs(p, exist_ok=True)
    if not IS_WIN:
        os.chmod(p, 0o700)
    if separate:
        for s in WORK_DATA:
            dst = os.path.join(p, s)
            if is_link(dst) or (os.path.isfile(dst) and same(dst, os.path.join(base, s))):
                unlink(dst)  # only the link goes; the shared data stays where it is
                if s in SHARED_DIRS:
                    os.makedirs(dst)
    for s in SHARED_DIRS:
        if separate and s in WORK_DATA:
            continue
        dst, src = os.path.join(p, s), os.path.join(base, s)
        os.makedirs(src, exist_ok=True)
        if os.path.lexists(dst):
            if is_link(dst) or same(dst, src):
                continue  # already linked (or linked elsewhere on purpose)
            try:
                os.rmdir(dst)  # an empty folder Claude created before the link existed
            except OSError:
                continue  # has its own content: leave it alone
        link_dir(src, dst)
    for s in SHARED_FILES:
        if separate and s in WORK_DATA:
            continue
        dst, src = os.path.join(p, s), os.path.join(base, s)
        if same(dst, src):
            continue
        if os.path.lexists(dst):
            if is_link(dst):
                if os.path.exists(dst):
                    continue  # links somewhere else on purpose
                os.remove(dst)  # a broken link
            elif not os.path.exists(src) or os.path.getmtime(dst) > os.path.getmtime(src):
                # Claude saved this file by replacing the link with a real file: the
                # profile's copy is newer, so it becomes the shared one. The old shared
                # copy is kept as a dated backup. Contents are copied rather than the
                # file moved, so a ~/.claude file that is itself a link (for example
                # into a dotfiles repo) stays a link.
                import shutil
                if os.path.exists(src):
                    shutil.copy2(src, "%s.hats-bak-%s" % (src, time.strftime("%Y%m%d-%H%M%S")))
                shutil.copyfile(dst, src)
                os.remove(dst)
            else:
                os.replace(dst, dst + ".hats-bak")
        if os.path.exists(src):
            link_file(src, dst)
    seed(p, base)


def seed(p, base=BASE):
    """First launch of a new profile: carry over onboarding and per-project trust,
    MCP and permission state from the main config — never the account itself."""
    main = os.path.join(HOME, ".claude.json") if norm(base) == norm(BASE) else os.path.join(base, ".claude.json")
    dst, src = os.path.join(p, ".claude.json"), main
    if os.path.exists(dst):
        return
    a = read_json(src)
    if not isinstance(a, dict):
        return
    top = ["hasCompletedOnboarding", "lastOnboardingVersion", "lastReleaseNotesSeen",
           "installMethod", "autoUpdates", "autoUpdatesProtectedForNative", "migrationVersion",
           "opusProMigrationComplete", "sonnet1m45MigrationComplete",
           "hasCompletedClaudeInChromeOnboarding", "mcpServers"]
    per = ["allowedTools", "mcpServers", "enabledMcpjsonServers", "disabledMcpjsonServers",
           "hasTrustDialogAccepted", "hasClaudeMdExternalIncludesApproved",
           "hasClaudeMdExternalIncludesWarningShown"]
    out = {k: a[k] for k in top if a.get(k) is not None}
    out["projects"] = {path: {k: v[k] for k in per if v.get(k) is not None}
                       for path, v in (a.get("projects") or {}).items() if isinstance(v, dict)}
    try:
        fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(out, f)


def remove_profile_dir(path):
    """Delete a profile folder. Links inside it are removed as links, so nothing
    shared with ~/.claude is ever deleted. Refuses anything outside ~/.claude-profiles."""
    if not inside(path, PROFILES_DIR) or norm(path) == norm(PROFILES_DIR):
        raise Fail("hat: refusing to delete %s: not a folder inside %s" % (path, PROFILES_DIR))
    if is_link(path):
        unlink(path)
        return

    root = norm(path)

    def walk(d):
        for e in os.scandir(d):
            if is_link(e.path) or not inside(e.path, root):
                unlink(e.path)  # a link: remove it, never what it points to
            elif e.is_dir(follow_symlinks=False):
                walk(e.path)
            else:
                remove_file(e.path)  # for a hard link this drops only this name
        os.rmdir(d)

    if os.path.isdir(path):
        walk(path)


# ------------------------------------------------------------------ account facts

def files_of(d):
    """Claude Code's account file and credentials file for a config folder."""
    if d == "native":
        return os.path.join(HOME, ".claude.json"), os.path.join(BASE, ".credentials.json")
    return os.path.join(d, ".claude.json"), os.path.join(d, ".credentials.json")


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


def login_of(d):
    """email, org (empty for a personal account), plan, signed in — from Claude's own files.
    Linux and Windows keep the token in .credentials.json; macOS keeps it in the
    Keychain, so there the account record in .claude.json is what tells."""
    cfg, cred = files_of(d)
    account = (read_json(cfg) or {}).get("oauthAccount") or {}
    email = account.get("emailAddress") or ""
    org = account.get("organizationName") or ""
    if re.search(r"@.*s Organization$", org):
        org = ""  # the automatic name of a personal account says nothing new
    plan, signed_in = "", bool(email)
    if os.path.exists(cred):
        o = (read_json(cred) or {}).get("claudeAiOauth") or {}
        signed_in = bool(email and o.get("accessToken"))
        s, t = o.get("subscriptionType") or "", o.get("rateLimitTier") or ""
        plan = s[:1].upper() + s[1:] + (" 20x" if "20x" in t else " 5x" if "5x" in t else "")
    elif not IS_MAC:
        signed_in = False
    return {"email": email, "org": org, "plan": plan, "in": signed_in}


_cache = None


def info(cfg, p):
    """Login facts, state and usage for a profile. The login part is cached by the
    files' modification times: the main .claude.json can be large and this runs on
    every prompt."""
    global _cache
    d = cfg.pdir.get(p, "")
    path = os.path.join(CONF_DIR, "cache.json")
    if _cache is None:
        _cache = read_json(path) or {}
    # Claude rewrites .claude.json all the time (it can be megabytes); the login only
    # changes when the credentials file does, so that is the key where it exists.
    cfg_file, cred_file = files_of(d)
    sig = "%s|%s" % (d, mtime(cred_file) if os.path.exists(cred_file) else mtime(cfg_file))
    hit = _cache.get(p)
    if hit and hit.get("sig") == sig:
        i = hit["info"]
    else:
        i = login_of(d) if d else {"email": "", "org": "", "plan": "", "in": False}
        _cache[p] = {"sig": sig, "info": i}
        try:
            write_atomic(path, json.dumps(_cache))
        except OSError:
            pass
    want = cfg.pmail.get(p, "")
    state = "out" if not i["in"] else "wrong" if want and i["email"].lower() != want.lower() else "ok"
    u5, uw, r5, rw = usage(p) if state == "ok" else (None, None, None, None)
    return dict(i, state=state, want=want, u5=u5, uw=uw, r5=r5, rw=rw)


def usage(p):
    """Share of the 5-hour and weekly limits used, as last reported by a Claude
    session on this profile (the status line records it). None when unknown."""
    try:
        with open(os.path.join(CONF_DIR, "usage", p), encoding="utf-8") as f:
            v = f.read().strip().split("|")
    except OSError:
        return None, None, None, None
    v += [""] * (4 - len(v))

    def value(used, resets_at):
        if not used.isdigit():
            return None
        return 0 if resets_at.isdigit() and time.time() > int(resets_at) else int(used)

    def reset(resets_at):
        return int(resets_at) if resets_at.isdigit() and time.time() < int(resets_at) else None

    return value(v[0], v[1]), value(v[2], v[3]), reset(v[1]), reset(v[3])


# ------------------------------------------------------------------ rendering

def label_of(cfg, p, i, pinned=False, wrap=False):
    """The account marker: the name in its colour; grey when signed out, ⚠ red when
    signed in with the wrong email. wrap=True only for the prompt."""
    col = {"out": GREY, "wrong": RED}.get(i["state"], cfg.color(p))
    text = ("⚠ " if i["state"] == "wrong" else "") + p + (" · pinned" if pinned else "")
    if cfg.style == "badge":
        return (hide(sgr("38;5;%d" % col), wrap) + "▐" + hide(sgr("1;38;5;16;48;5;%d" % col), wrap)
                + text + hide(sgr("0;38;5;%d" % col), wrap) + "▌" + hide(sgr("0"), wrap))
    if cfg.style == "minimal":
        text = "(" + text + ")"
    return hide(sgr("1;38;5;%d" % col), wrap) + text + hide(sgr("0"), wrap)


def detail(p, i):
    """Who a profile is signed in as, or what is wrong with it."""
    red, off = sgr("1;38;5;%d" % RED), sgr("0")
    if i["state"] == "out":
        return "%snot signed in%s — run: hat login %s" % (red, off, p)
    if i["state"] == "wrong":
        return "%swrong account%s %s — should be %s" % (red, off, i["email"], i["want"])
    return " · ".join(x for x in (i["email"], i["org"], i["plan"]) if x)


def pct(label, n):
    """"label N%", the number yellow from 50% and red from 80%."""
    col = RED if n >= 80 else YELLOW if n >= 50 else DIMGREY
    return "%s%s%s%s %d%%%s" % (sgr("2"), label, sgr("0"), sgr("38;5;%d" % col), n, sgr("0"))


def usage_text(i):
    return " · ".join(pct(label, n) for label, n in (("5h", i["u5"]), ("week", i["uw"])) if n is not None)


def describe(cfg, pin=None):
    """One line about the profile in effect: name, who, usage, and why."""
    pin = os.environ.get("HAT_PIN", "") if pin is None else pin
    p, why = cfg.resolve(pin)
    i = info(cfg, p)
    u = usage_text(i)
    line = "%s→ %s%s%s  %s%s  %s(%s)%s" % (
        sgr("1;38;5;%d" % cfg.color(p)), p, " · pinned" if pin else "", sgr("0"),
        detail(p, i), "  ·  " + u if u else "", sgr("2"), why, sgr("0"))
    return line, i


def rows(cfg, pin):
    """An aligned "name  who  usage" line per profile, plus each one's state."""
    labels, details, usages, states = [], [], [], []
    for p in cfg.names:
        i = info(cfg, p)
        labels.append(label_of(cfg, p, i, p == pin))
        details.append(detail(p, i) + (sgr("2") + " · separate" + sgr("0") if p in cfg.separate else ""))
        usages.append(usage_text(i))
        states.append(i["state"])
    w = max([plain_len(x) for x in labels] or [0])
    dw = max([plain_len(d) for d, u in zip(details, usages) if u] or [0])
    out = []
    for label, d, u in zip(labels, details, usages):
        line = label + " " * (w - plain_len(label)) + "  " + d
        if u:
            line += " " * (dw - plain_len(d) + 3) + u
        out.append(line)
    return out, states


# ------------------------------------------------------------------ running programs

def env_for(cfg, p):
    """The environment that makes Claude Code use profile p."""
    d = cfg.dir(p)
    env = dict(os.environ, HAT_PROFILE=p)
    if d == "native":
        env.pop("CLAUDE_CONFIG_DIR", None)
    else:
        cfg.links(p)  # a folder you chose yourself is used as it is
        env["CLAUDE_CONFIG_DIR"] = d
    return env


def run(cmd, env, to_stderr=False, handover=False):
    """Run a program. With handover=True, on Linux and macOS Hats is replaced by it,
    so Ctrl-C, Ctrl-Z and exit codes behave exactly as if it had been started
    directly. Otherwise Hats waits, ignoring Ctrl-C itself so the program decides."""
    import shutil
    import signal
    import subprocess
    exe = shutil.which(cmd[0], path=env.get("PATH"))
    if not exe:
        raise Fail("hat: '%s' not found on PATH" % cmd[0])
    if handover and not IS_WIN and not to_stderr:
        sys.stdout.flush()
        sys.stderr.flush()
        os.execve(exe, [exe] + cmd[1:], env)
    old = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        return subprocess.call([exe] + cmd[1:], env=env, stdout=sys.stderr if to_stderr else None)
    finally:
        signal.signal(signal.SIGINT, old)


def shell_set(var, value):
    if Out.shell == "pwsh":
        return "$env:%s = '%s'" % (var, value.replace("'", "''"))
    return "export %s='%s'" % (var, value.replace("'", "'\\''"))


def shell_unset(var):
    if Out.shell == "pwsh":
        return "Remove-Item Env:%s -ErrorAction SilentlyContinue" % var
    return "unset %s" % var


def confirm(question):
    if not sys.stdin.isatty():
        raise Fail("hat: %s Run it in a terminal, or add --yes." % question)
    Out.stream.write(question + " [y/N] ")
    Out.stream.flush()
    return sys.stdin.readline().strip().lower().startswith("y")


# ------------------------------------------------------------------ the menu

def read_key():
    """One keypress: 'up', 'down', 'enter', 'esc', or the character typed."""
    if IS_WIN:
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
        return {"\r": "enter", "\x1b": "esc", "\x03": "esc", "q": "esc"}.get(ch, ch)
    import select
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1).decode("utf-8", "replace")
        if ch == "\x1b":
            while len(ch) < 3 and select.select([fd], [], [], 0.05)[0]:
                ch += os.read(fd, 1).decode("utf-8", "replace")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return {"\x1b[A": "up", "\x1bOA": "up", "k": "up", "\x1b[B": "down", "\x1bOB": "down",
            "j": "down", "\r": "enter", "\n": "enter", "\x1b": "esc", "\x03": "esc",
            "q": "esc"}.get(ch, ch)


def menu(cfg):
    """Arrow-key menu. Returns a profile name, "auto", or None when cancelled."""
    pin = os.environ.get("HAT_PIN", "")
    lines, _ = rows(cfg, pin)
    here, _ = cfg.auto()
    cur, _ = cfg.resolve(pin)
    n = len(cfg.names)
    sel = cfg.names.index(cur) if cur in cfg.names else n
    say("\n  %sClaude account for this terminal%s\n  %s↑/↓ move · Enter select · 1-%d or a to jump · q cancel%s\n"
        % (sgr("1"), sgr("0"), sgr("2"), n, sgr("0")))
    w = Out.stream
    while True:
        for k, line in enumerate(lines):
            mark = sgr("1") + "▸" + sgr("0") if k == sel else " "
            w.write("\r\x1b[K %s %s%d%s %s\n" % (mark, sgr("2"), k + 1, sgr("0"), line))
        mark = sgr("1") + "▸" + sgr("0") if sel == n else " "
        w.write("\r\x1b[K %s %sa%s  %sauto%s  follow the folder — here that means %s%s%s%s\n" % (
            mark, sgr("2"), sgr("0"), sgr("1"), sgr("0"), sgr("1"), here, sgr("0"),
            "  " + sgr("2") + "(in effect now)" + sgr("0") if not pin else ""))
        w.flush()
        key = read_key()
        if key == "esc":
            say("\n  no change\n")
            return None
        if key == "enter":
            break
        if key == "a":
            sel = n
            break
        if key.isdigit() and 1 <= int(key) <= n:
            sel = int(key) - 1
            break
        if key in ("up", "down"):
            sel = (sel + (n if key == "up" else 1)) % (n + 1)
        w.write("\x1b[%dA" % (n + 1))  # back to the top of the list to redraw it
    say()
    return "auto" if sel == n else cfg.names[sel]


# ------------------------------------------------------------------ commands
# Each takes (cfg, args, emit). emit is a list of shell lines for the hook to run
# in --eval mode, or None when hat.py was called without --eval.

def need_hook(emit):
    if emit is None:
        raise Fail("hat: switching needs the shell integration. Open a new terminal after "
                   "installing, or use: hat run <profile>")


def cmd_pick(cfg, args, emit):
    need_hook(emit)
    choice = menu(cfg)
    if choice == "auto":
        cmd_auto(cfg, [], emit)
    elif choice:
        cmd_use(cfg, [choice], emit)
        if info(cfg, choice)["state"] == "out" and confirm("Sign in to '%s' now?" % choice):
            cmd_login(cfg, [choice], emit)


def cmd_use(cfg, args, emit):
    if not args:
        raise Fail("usage: hat use <profile>")
    p = args[0]
    d = cfg.dir(p)
    need_hook(emit)
    env = env_for(cfg, p)
    if "CLAUDE_CONFIG_DIR" in env:
        emit.append(shell_set("CLAUDE_CONFIG_DIR", env["CLAUDE_CONFIG_DIR"]))
    else:
        emit.append(shell_unset("CLAUDE_CONFIG_DIR"))
    emit.append(shell_set("HAT_PIN", p))
    say(describe(cfg, pin=p)[0])


def cmd_auto(cfg, args, emit):
    need_hook(emit)
    emit.append(shell_unset("HAT_PIN"))
    emit.append(shell_unset("CLAUDE_CONFIG_DIR"))
    say(describe(cfg, pin="")[0])


def cmd_status(cfg, args, emit):
    pin = os.environ.get("HAT_PIN", "")
    if "--json" in args:
        cur, why = cfg.resolve(pin)
        profiles = []
        for p in cfg.names:
            i = info(cfg, p)
            profiles.append({"name": p, "folder": cfg.pdir[p], "email": i["email"], "org": i["org"],
                             "plan": i["plan"], "state": i["state"], "expected_email": i["want"],
                             "separate": p in cfg.separate, "usage_5h": i["u5"], "usage_week": i["uw"]})
        sys.stdout.write(json.dumps({"version": VERSION, "active": cur, "reason": why, "pinned": bool(pin),
                                     "default": cfg.default, "profiles": profiles,
                                     "rules": [{"profile": p, "folder": d} for p, d in cfg.rules]},
                                    indent=2) + "\n")
        return
    lines, _ = rows(cfg, pin)
    cur, why = cfg.resolve(pin)
    say()
    for p, line in zip(cfg.names, lines):
        say(" %s %s" % (sgr("1") + "▸" + sgr("0") if p == cur else " ", line))
    say("\n  In effect here: %s%s%s  %s(%s)%s\n\n  Folder rules"
        % (sgr("1"), cur, sgr("0"), sgr("2"), why, sgr("0")))
    for p, d in cfg.rules:
        say("    %-10s %s" % (p, d))
    say("    %-10s %s\n" % (cfg.default, "(everywhere else)"))


def cmd_which(cfg, args, emit):
    say(cfg.resolve()[0])


def cmd_names(cfg, args, emit):
    say("\n".join(cfg.names))


def cmd_add(cfg, args, emit):
    sep = "--separate" in args
    args = [a for a in args if a != "--separate"]
    if not args:
        raise Fail("usage: hat add <name> [login email] [--separate]")
    p, email = args[0], (args[1] if len(args) > 1 else "")
    if not re.match(r"^[A-Za-z0-9_-]+$", p):
        raise Fail("hat: use letters, digits, - or _ in the name")
    if p in cfg.pdir:
        raise Fail("hat: profile '%s' already exists" % p)
    edit_conf(add=("profile %s ~/.claude-profiles/%s %s" % (p, p, email)).rstrip())
    if sep:
        edit_conf(add="separate %s" % p)
    ensure_links(os.path.join(PROFILES_DIR, p), cfg.base, sep)
    say("added '%s'%s — sign in with: hat login %s"
        % (p, " (its history and memory stay separate)" if sep else "", p))


def cmd_remove(cfg, args, emit):
    """Sign a profile out on this computer, delete its folder and its rules.
    Shared history, memory and settings are not touched."""
    if not args:
        raise Fail("usage: hat remove <profile> [--yes]")
    p = args[0]
    d = cfg.dir(p)
    if d == "native":
        raise Fail("hat: '%s' is your main Claude login (~/.claude); hat never removes it" % p)
    if p == cfg.default:
        raise Fail("hat: '%s' is the default profile. Pick another first: hat default <profile>" % p)
    ours = inside(d, PROFILES_DIR)
    what = "delete %s" % tilde(d) if ours else "forget it (its folder %s stays)" % tilde(d)
    if "--yes" not in args and "-y" not in args:
        if not confirm("Remove profile '%s'? This signs it out on this computer and will %s. "
                       "Shared history and settings stay." % (p, what)):
            say("no change")
            return
    if os.path.isdir(d) and info(cfg, p)["state"] != "out":
        env = dict(os.environ, CLAUDE_CONFIG_DIR=d)
        try:
            run(["claude", "auth", "logout"], env, to_stderr=True)
        except Fail:
            pass  # claude is not installed; deleting the folder still removes the login
    if ours:
        remove_profile_dir(d)
    edit_conf(drop=lambda bits: bits[0] in ("profile", "dir", "separate") and bits[1] == p)
    try:
        os.remove(os.path.join(CONF_DIR, "usage", p))
    except OSError:
        pass
    say("removed '%s'" % p)
    if os.environ.get("HAT_PIN") == p:
        say("This terminal was pinned to it; run: hat auto")


def cmd_login(cfg, args, emit):
    if not args:
        raise Fail("usage: hat login <profile>")
    p = args[0]
    want = cfg.pmail.get(p, "")
    rc = run(["claude", "auth", "login"] + (["--email", want] if want else []),
             env_for(cfg, p), to_stderr=Out.stream is sys.stderr)
    if rc:
        return rc
    i = info(cfg, p)
    if i["state"] == "wrong":
        # Never leave a profile usable with someone else's account.
        run(["claude", "auth", "logout"], env_for(cfg, p), to_stderr=True)
        say("%s The browser approved %s, not %s, so Hats signed it out again."
            % (label_of(cfg, p, i), i["email"], want))
        say("Sign out of claude.ai in the browser (or paste the login link into a private window),")
        say("sign in as %s, then run: hat login %s" % (want, p))
        return 1
    say("%s %s" % (label_of(cfg, p, i), detail(p, i)))
    return 0


def cmd_map(cfg, args, emit):
    if not args:
        raise Fail("usage: hat map <profile> [directory]")
    cfg.dir(args[0])
    d = args[1] if len(args) > 1 else "."
    if not os.path.isdir(d):
        raise Fail("hat: no such folder: %s" % d)
    d = os.path.realpath(d)
    edit_conf(drop=is_rule_for(d), add="dir %s %s" % (args[0], d))
    say("%s → %s" % (d, args[0]))


def cmd_unmap(cfg, args, emit):
    d = os.path.abspath(args[0] if args else ".")
    edit_conf(drop=is_rule_for(d))
    say("removed rule for %s" % d)


def cmd_default(cfg, args, emit):
    if not args:
        raise Fail("usage: hat default <profile>")
    cfg.dir(args[0])
    edit_conf(set_key=("default", args[0]))
    say("default → %s" % args[0])


def cmd_style(cfg, args, emit):
    if args and args[0] in STYLES:
        edit_conf(set_key=("style", args[0]))
        return
    say("usage: hat style <clean|badge|minimal>   (now: %s)" % cfg.style)
    say("  clean    the account name in its colour")
    say("  badge    the name in a filled colour block")
    say("  minimal  (name)")


def cmd_claude(cfg, args, emit):
    """`claude` starts on the account shown in the prompt."""
    if os.environ.get("CLAUDECODE"):  # inside a Claude Code session: keep its account
        return run(["claude"] + args, dict(os.environ), handover=True)
    p, _ = cfg.resolve()
    if p not in cfg.pdir:
        raise Fail("hat: this terminal is pinned to '%s', which no longer exists. Run: hat auto" % p)
    env = env_for(cfg, p)
    line, i = describe(cfg)
    if i["state"] == "wrong":
        raise Fail("hat: not starting Claude: '%s' is signed in as %s, but should be %s.\n"
                   "Sign in again with: hat login %s   (to start anyway: hat run %s)"
                   % (p, i["email"], i["want"], p, p))
    if i["state"] != "ok" and sys.stderr.isatty():
        sys.stderr.write(line + "\n")
    for label, used, resets in (("5-hour", i["u5"], i["r5"]), ("weekly", i["uw"], i["rw"])):
        if used is not None and used >= WARN_AT:
            sys.stderr.write("%shat: '%s' has used %d%% of its %s limit%s.%s\n" % (
                sgr("38;5;%d" % YELLOW), p, used, label,
                time.strftime(" (resets %a %H:%M)", time.localtime(resets)) if resets else "", sgr("0")))
    return run(["claude"] + args, env, handover=True)


def cmd_run(cfg, args, emit):
    if not args:
        raise Fail("usage: hat run <profile> [claude args...]")
    return run(["claude"] + args[1:], env_for(cfg, args[0]), handover=True)


def cmd_exec(cfg, args, emit):
    if len(args) < 2:
        raise Fail("usage: hat exec <profile> <command...>")
    return run(args[1:], env_for(cfg, args[0]), handover=True)


def cmd_edit(cfg, args, emit):
    import shlex
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or ("notepad" if IS_WIN else "nano")
    return run(shlex.split(editor, posix=not IS_WIN) + [CONF], dict(os.environ), handover=True)


def cmd_help(cfg, args, emit):
    say(HELP.rstrip())


def cmd_prompt(cfg, args, emit):
    """For the hooks: the marker for the prompt, then \\x1f, then the tab title.
    For bash the title escape is already part of the marker."""
    pin = os.environ.get("HAT_PIN", "")
    p, _ = cfg.resolve(pin)
    title = "%s%s — %s" % (p, " (pinned)" if pin else "", tilde(os.getcwd()))
    seg = label_of(cfg, p, info(cfg, p), bool(pin), wrap=True) + " "
    if Out.shell == "bash":
        seg = hide("\x1b]0;" + title + "\x07") + seg
    sys.stdout.write(seg + "\x1f" + title)


def cmd_statusline(cfg, args, emit):
    """Claude Code's status line (settings.json "statusLine"). Claude sends the
    session state as JSON on stdin; this also records the account's usage."""
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    d = os.environ.get("CLAUDE_CONFIG_DIR") or "native"
    p = cfg.profile_for_dir(d)

    def num(path):
        v = data
        for k in path.split("."):
            v = v.get(k) if isinstance(v, dict) else None
        return int(v) if isinstance(v, (int, float)) else None

    ctx = num("context_window.used_percentage")
    u5, r5 = num("rate_limits.five_hour.used_percentage"), num("rate_limits.five_hour.resets_at")
    uw, rw = num("rate_limits.seven_day.used_percentage"), num("rate_limits.seven_day.resets_at")
    if p and (u5 is not None or uw is not None):
        try:
            os.makedirs(os.path.join(CONF_DIR, "usage"), exist_ok=True)
            write_atomic(os.path.join(CONF_DIR, "usage", p),
                         "|".join("" if x is None else str(x) for x in (u5, r5, uw, rw)) + "\n")
        except OSError:
            pass

    bar = "  " + sgr("2") + "│" + sgr("0") + "  "
    if p:
        i = info(cfg, p)
        who = detail(p, i)
        if i["state"] == "ok":
            who = " · ".join(x for x in (i["org"] or i["email"], i["plan"]) if x)
        out = label_of(cfg, p, i) + "  " + who
    else:
        out = sgr("1") + "custom config" + sgr("0") + "  " + tilde(d)
    model = (data.get("model") or {}).get("display_name") or ""
    effort = (data.get("effort") or {}).get("level") or ""
    if model:
        out += bar + model + (" · " + effort if effort else "")
    nums = [pct(label, v) for label, v in (("context", ctx), ("5h", u5), ("week", uw)) if v is not None]
    if nums:
        out += bar + " · ".join(nums)
    sys.stdout.write(out)


def link_problems(cfg, p):
    """What a managed profile should share with the base folder but does not, and
    (for a separate profile) what it shares but should not."""
    d, problems = cfg.pdir[p], []
    sep = p in cfg.separate
    for s in SHARED_DIRS + SHARED_FILES:
        src, dst = os.path.join(cfg.base, s), os.path.join(d, s)
        if sep and s in WORK_DATA:
            if os.path.exists(src) and same(dst, src):
                problems.append(s + " (shared, but the profile is separate)")
        elif os.path.exists(src) and not same(dst, src):
            problems.append(s)
    return problems


def cmd_doctor(cfg, args, emit):
    """Check everything Hats depends on; --fix repairs profile links."""
    import shutil
    fix, problems = "--fix" in args, []

    def good(msg):
        say("  %s✓%s %s" % (sgr("38;5;114"), sgr("0"), msg))

    def bad(msg, hint):
        problems.append(msg)
        say("  %s✗%s %s\n      %s%s%s" % (sgr("1;38;5;%d" % RED), sgr("0"), msg, sgr("2"), hint, sgr("0")))

    say("\n  Hats %s · Python %s · %s\n" % (VERSION, sys.version.split()[0], sys.platform))
    exe = shutil.which("claude")
    if exe:
        good("Claude Code found: %s" % exe)
    else:
        bad("Claude Code is not on PATH", "Install Claude Code, then open a new terminal.")
    if os.environ.get("HAT_HOOK"):
        good("this terminal has the Hats hook (%s)" % os.environ["HAT_HOOK"])
    else:
        bad("this terminal has no Hats hook, so `claude` is not switched",
            "Open a new terminal. If that does not help, run install.py again.")

    if cfg.default not in cfg.pdir:
        bad("the default profile '%s' does not exist" % cfg.default, "Fix: hat default <profile>")
    pin = os.environ.get("HAT_PIN")
    if pin and pin not in cfg.pdir:
        bad("this terminal is pinned to '%s', which does not exist" % pin, "Fix: hat auto")
    for p, d in cfg.rules:
        if p not in cfg.pdir:
            bad("a folder rule names an unknown profile '%s' (%s)" % (p, d), "Fix: hat unmap %s" % d)
        elif not os.path.isdir(d):
            bad("a folder rule points to a missing folder: %s" % d, "Fix: hat unmap %s" % d)

    for p in cfg.names:
        d = cfg.pdir[p]
        if d != "native" and not os.path.isdir(d):
            bad("%s: its folder %s is missing" % (p, tilde(d)), "Fix: hat remove %s, then hat add %s" % (p, p))
            continue
        broken = link_problems(cfg, p) if cfg.managed(p) else []
        if broken and fix:
            cfg.links(p)
            broken = link_problems(cfg, p)
        i = info(cfg, p)
        if broken:
            bad("%s: not linked as it should be: %s" % (p, ", ".join(broken)), "Fix: hat doctor --fix")
        if i["state"] == "out":
            bad("%s: not signed in" % p, "Fix: hat login %s" % p)
        elif i["state"] == "wrong":
            bad("%s: signed in as %s, should be %s" % (p, i["email"], i["want"]), "Fix: hat login %s" % p)
        elif not broken:
            good("%s: %s" % (p, detail(p, i)))

    line = ((read_json(os.path.join(cfg.base, "settings.json")) or {}).get("statusLine") or {}).get("command", "")
    if "hat.py" in line:
        good("Claude Code's status line shows the account")
    else:
        say("  %s· Claude Code's status line is not the Hats one (optional)%s" % (sgr("2"), sgr("0")))

    if problems:
        say("\n  %d problem%s found.\n" % (len(problems), "" if len(problems) == 1 else "s"))
        return 1
    say("\n  All good.\n")
    return 0


def cmd_update(cfg, args, emit):
    """Pull the latest version into the repository Hats was installed from, and reinstall."""
    import subprocess
    meta = read_json(os.path.join(CONF_DIR, "install.json")) or {}
    repo = meta.get("repo", "")
    if not os.path.isdir(os.path.join(repo, ".git")):
        raise Fail("hat: cannot tell which repository Hats was installed from. Pull it yourself "
                   "and run its install.py again.")
    say("Updating from %s" % repo)
    if subprocess.call(["git", "-C", repo, "pull", "--ff-only"]) != 0:
        raise Fail("hat: git pull did not succeed (see above); nothing was changed.")
    cmd = [sys.executable, os.path.join(repo, "install.py")]
    if meta.get("shells"):
        cmd += ["--shell", ",".join(meta["shells"])]
    return subprocess.call(cmd)


def cmd_export(cfg, args, emit):
    """Profiles, folder rules and options as JSON. Never logins."""
    data = {"hats": VERSION, "default": cfg.default, "style": cfg.style,
            "profiles": [{"name": p, "folder": "native" if cfg.pdir[p] == "native" else tilde(cfg.pdir[p]),
                          "email": cfg.pmail[p], "separate": p in cfg.separate} for p in cfg.names],
            "rules": [{"profile": p, "folder": tilde(d)} for p, d in cfg.rules]}
    text = json.dumps(data, indent=2) + "\n"
    if args:
        write_atomic(args[0], text)
        say("saved %d profiles and %d folder rules to %s (no logins)" % (len(cfg.names), len(cfg.rules), args[0]))
    else:
        sys.stdout.write(text)


def cmd_import(cfg, args, emit):
    """Add the profiles and folder rules from an export. Nothing existing is changed."""
    if not args:
        raise Fail("usage: hat import <file>")
    data = read_json(args[0])
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), list):
        raise Fail("hat: %s is not a hat export" % args[0])
    added, skipped = [], []
    for prof in data["profiles"]:
        name, folder = str(prof.get("name", "")), str(prof.get("folder") or "")
        if not re.match(r"^[A-Za-z0-9_-]+$", name) or name in cfg.pdir or folder == "native":
            skipped.append(name)
            continue
        folder = folder or "~/.claude-profiles/" + name
        edit_conf(add=("profile %s %s %s" % (name, folder, prof.get("email") or "")).rstrip())
        if prof.get("separate"):
            edit_conf(add="separate %s" % name)
        added.append(name)
    cfg = Config()
    for name in added:
        cfg.links(name)
    rules = 0
    for r in data.get("rules") or []:
        p, d = str(r.get("profile", "")), expand(str(r.get("folder", "")))
        if p in cfg.pdir and d and not any(norm(d) == norm(x) for _, x in cfg.rules):
            edit_conf(add="dir %s %s" % (p, d))
            cfg.rules.append((p, d))
            rules += 1
    say("imported %d profile%s and %d folder rule%s" % (len(added), "" if len(added) == 1 else "s",
                                                        rules, "" if rules == 1 else "s"))
    if skipped:
        say("kept as they are here: %s" % ", ".join(n for n in skipped if n))
    for name in added:
        say("  sign in: hat login %s" % name)


def cmd_code(cfg, args, emit):
    """Open VS Code, Cursor or Windsurf so that its Claude extension uses a profile.
    Editors reuse a window that is already open, which keeps that window's account,
    so a profile's editor gets its own window settings (extensions stay shared)."""
    args = list(args)
    editor = "code"
    if "--editor" in args:
        i = args.index("--editor")
        editor = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    if editor not in EDITORS:
        raise Fail("hat: --editor must be one of: %s" % ", ".join(EDITORS))
    if not args:
        raise Fail("usage: hat code <profile> [folder] [--editor code|cursor|windsurf]")
    p, folder = args[0], (args[1] if len(args) > 1 else ".")
    exe, extensions = EDITORS[editor]
    env = env_for(cfg, p)
    cmd = [exe]
    if cfg.pdir[p] != "native":
        cmd += ["--user-data-dir", os.path.join(cfg.pdir[p], "editor", editor),
                "--extensions-dir", expand(extensions)]
    say("opening %s on '%s'" % (editor, p))
    return run(cmd + [folder], env)


def cmd_context(cfg, args, emit):
    """For Claude Code's SessionStart hook: tell Claude which account it runs on."""
    p = cfg.profile_for_dir(os.environ.get("CLAUDE_CONFIG_DIR") or "native")
    if not p:
        return
    i = info(cfg, p)
    who = ", ".join(x for x in (i["email"], i["org"]) if x)
    sys.stdout.write("This Claude Code session runs on the Claude account profile '%s'%s, chosen with "
                     "Hats (a tool for using several Claude accounts on one computer).\n"
                     % (p, " (%s)" % who if who else ""))


def cmd_version(cfg, args, emit):
    say("hat %s" % VERSION)


COMMANDS = {
    "pick": cmd_pick, "use": cmd_use, "auto": cmd_auto,
    "status": cmd_status, "list": cmd_status, "ls": cmd_status,
    "which": cmd_which, "names": cmd_names,
    "add": cmd_add, "remove": cmd_remove, "rm": cmd_remove, "login": cmd_login,
    "map": cmd_map, "unmap": cmd_unmap, "default": cmd_default, "style": cmd_style,
    "claude": cmd_claude, "run": cmd_run, "exec": cmd_exec, "edit": cmd_edit,
    "help": cmd_help, "-h": cmd_help, "--help": cmd_help,
    "prompt": cmd_prompt, "statusline": cmd_statusline, "context": cmd_context,
    "doctor": cmd_doctor, "update": cmd_update, "export": cmd_export, "import": cmd_import,
    "code": cmd_code, "version": cmd_version, "--version": cmd_version,
}


def main(argv):
    emit = None
    while argv and argv[0] in ("--shell", "--eval"):
        if argv[0] == "--shell":
            Out.shell = argv[1] if len(argv) > 1 else Out.shell
            argv = argv[2:]
        else:
            emit, Out.stream = [], sys.stderr
            argv = argv[1:]
    if Out.shell == "pwsh":
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # the PowerShell hook reads it as UTF-8
        except AttributeError:
            pass
    enable_vt()
    cfg = Config()
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    if not cmd:
        cmd = "pick" if sys.stdin.isatty() and Out.stream.isatty() and emit is not None else "status"
    if cmd not in COMMANDS:
        raise Fail("hat: unknown command '%s' (try: hat help)" % cmd)
    rc = COMMANDS[cmd](cfg, args, emit)
    if emit:
        sys.stdout.write("\n".join(emit) + "\n")
    return rc or 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Fail as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(2)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:  # a bug in Hats must not hide how to keep working
        sys.stderr.write("hat: unexpected error: %r\nTo run Claude without hat: command claude "
                         "(PowerShell: claude.exe). Please report this.\n" % (e,))
        sys.exit(3)
