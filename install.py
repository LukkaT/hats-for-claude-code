#!/usr/bin/env python3
"""hat installer — Linux, macOS and Windows.

  python3 install.py                      install, or update after pulling a new version
  python3 install.py --shell zsh,pwsh     choose the shells yourself (bash, zsh, pwsh)
  python3 install.py --uninstall          remove Hats; profiles, logins and settings stay
  python3 install.py --uninstall --purge  also sign out and delete every profile

What install touches:
  ~/.config/hats/                          the tool (hat.py and one hook per shell)
  your shell start-up file(s)             one line each, ending in "# hats: Claude Code accounts"
  ~/.claude/settings.json                 "statusLine", only if you have none yet, and one
                                          SessionStart hook that tells Claude its account
"""

import json
import os
import shlex
import shutil
import subprocess
import sys

if sys.version_info < (3, 8):
    sys.exit("hat needs Python 3.8 or newer (this is %s)." % sys.version.split()[0])

HOME = os.path.expanduser("~")
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(HOME, ".config", "hats")
PROFILES = os.path.join(HOME, ".claude-profiles")
# Claude Code's settings: in ~/.claude, or in the folder you point CLAUDE_CONFIG_DIR at.
SETTINGS = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(HOME, ".claude"),
                        "settings.json")
MARKER = "# hats: Claude Code accounts"
FILES = ["hat.py", "hat.bash", "hat.zsh", "hat.ps1"]
OLD_FILES = ["hat.sh", "statusline.sh"]  # from the first, bash-only version
SHELLS = ("bash", "zsh", "pwsh")


def say(text):
    print("  " + text)


def fwd(p):
    return p.replace("\\", "/")


PY = fwd(sys.executable)
STATUS_CMD = '"%s" "%s/hat.py" statusline' % (PY, fwd(DEST))
CONTEXT_CMD = '"%s" "%s/hat.py" context' % (PY, fwd(DEST))


# ------------------------------------------------------------------ which files

def powershell_profiles():
    """Profile script paths for PowerShell 7 (pwsh) and Windows PowerShell 5.1."""
    found = []
    for exe in ("pwsh", "powershell"):
        if not shutil.which(exe):
            continue
        try:
            out = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-Command",
                                  "$PROFILE.CurrentUserCurrentHost"],
                                 capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            continue
        if out and out not in found:
            found.append(out)
    return found


def bash_rc():
    """The file interactive bash reads. macOS Terminal starts login shells, which read
    the first of ~/.bash_profile, ~/.bash_login, ~/.profile — creating ~/.bash_profile
    when only ~/.profile exists would make bash stop reading ~/.profile."""
    if not IS_MAC:
        return os.path.join(HOME, ".bashrc")
    for name in (".bash_profile", ".bash_login", ".profile"):
        if os.path.exists(os.path.join(HOME, name)):
            return os.path.join(HOME, name)
    return os.path.join(HOME, ".bash_profile")


def targets(shells):
    """(shell, start-up file) pairs to install into."""
    if shells is None:
        login = os.path.basename(os.environ.get("SHELL", ""))
        shells = []
        if not IS_WIN:
            if login == "bash" or os.path.exists(bash_rc()):
                shells.append("bash")
            if login == "zsh" or os.path.exists(os.path.join(HOME, ".zshrc")):
                shells.append("zsh")
        if IS_WIN or shutil.which("pwsh"):
            shells.append("pwsh")
    out = []
    for s in shells:
        if s == "bash":
            out.append(("bash", bash_rc()))
        elif s == "zsh":
            out.append(("zsh", os.path.join(HOME, ".zshrc")))
        else:
            out.extend(("pwsh", p) for p in powershell_profiles())
    return out


def hook_line(shell):
    """The one line hat adds: which Python to use, and load the hook if it exists."""
    hook = fwd(os.path.join(DEST, "hat." + ("ps1" if shell == "pwsh" else shell)))
    if shell == "pwsh":
        q = lambda s: "'" + s.replace("'", "''") + "'"
        return "$env:HAT_PYTHON = %s; if (Test-Path -LiteralPath %s) { . %s }  %s" % (
            q(PY), q(hook), q(hook), MARKER)
    return "export HAT_PYTHON=%s; [ -f %s ] && . %s  %s" % (
        shlex.quote(PY), shlex.quote(hook), shlex.quote(hook), MARKER)


# ------------------------------------------------------------------ start-up files
# Read and written so that every other byte stays exactly as it was: the file's own
# encoding (UTF-16 profiles from Windows PowerShell included; anything else is kept
# byte for byte), its line endings, and its byte-order mark. Writing opens the file
# itself, so a start-up file that is a symlink stays one.

def encoding_of(raw):
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "utf-16"
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    return "utf-8"


def read_lines(path):
    """(lines, encoding), or (None, "utf-8") if the file does not exist."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return None, "utf-8"
    enc = encoding_of(raw)
    return raw.decode(enc, errors="surrogateescape").splitlines(keepends=True), enc


def write_lines(path, lines, enc):
    with open(path, "w", encoding=enc, errors="surrogateescape", newline="") as f:
        f.writelines(lines)


def strip_marker(path):
    """Remove the Hats line (and the blank line install put before it). Returns True if found."""
    lines, enc = read_lines(path)
    if lines is None:
        return False
    keep = []
    for line in lines:
        if MARKER in line:
            if keep and keep[-1].strip() == "":
                keep.pop()
            continue
        keep.append(line)
    if len(keep) == len(lines):
        return False
    write_lines(path, keep, enc)
    return True


def add_line(path, line):
    """Append the Hats line, replacing an earlier one."""
    strip_marker(path)
    lines, enc = read_lines(path)
    if lines is None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        lines = []
    eol = "\r\n" if any(x.endswith("\r\n") for x in lines) else "\n"
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += eol
    if lines:
        lines.append(eol)
    write_lines(path, lines + [line + eol], enc)


# ------------------------------------------------------------------ status line

def read_settings():
    """(settings, indent): {} if there is no file, None if it is not valid JSON
    (then Hats leaves it alone)."""
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            text = f.read()
        data = json.loads(text)
    except FileNotFoundError:
        return {}, 2
    except (OSError, ValueError):
        return None, 2
    second = text.split("\n")[1] if "\n" in text else ""
    indent = len(second) - len(second.lstrip(" ")) or 2
    return (data if isinstance(data, dict) else None), indent


def write_settings(data, indent):
    """Write in one step, in the file's own indent, keeping a symlink a symlink."""
    real = os.path.realpath(SETTINGS)
    os.makedirs(os.path.dirname(real), exist_ok=True)
    tmp = "%s.hats-%d.tmp" % (real, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
        f.write("\n")
    if os.path.exists(real):
        shutil.copymode(real, tmp)
    os.replace(tmp, real)


def is_ours(cmd):
    return cmd.rstrip().endswith('hat.py" statusline') or cmd.rstrip().endswith("hat/statusline.sh")


def is_our_context(entry):
    """A SessionStart matcher group that holds only the Hats context hook."""
    hooks = entry.get("hooks") if isinstance(entry, dict) else None
    return (isinstance(hooks, list) and len(hooks) == 1 and isinstance(hooks[0], dict)
            and str(hooks[0].get("command", "")).rstrip().endswith('hat.py" context'))


def without_context(data):
    """settings with the Hats SessionStart hook taken out; containers it emptied go too."""
    hooks = data.get("hooks")
    if not isinstance(hooks, dict) or not isinstance(hooks.get("SessionStart"), list):
        return data, False
    kept = [e for e in hooks["SessionStart"] if not is_our_context(e)]
    if len(kept) == len(hooks["SessionStart"]):
        return data, False
    if kept:
        hooks["SessionStart"] = kept
    else:
        del hooks["SessionStart"]
        if not hooks:
            del data["hooks"]
    return data, True


def with_context(data):
    """settings with the Hats SessionStart hook (replacing an older one of ours)."""
    data, _ = without_context(data)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        return data, False
    hooks.setdefault("SessionStart", []).append(
        {"hooks": [{"type": "command", "command": CONTEXT_CMD, "timeout": 10}]})
    return data, True


# ------------------------------------------------------------------ install

def install(shells):
    if not shutil.which("claude"):
        say("note: 'claude' is not on your PATH yet. Hats works once Claude Code is installed.")
    print("Installing Hats")
    os.makedirs(DEST, exist_ok=True)
    for f in FILES:
        shutil.copy2(os.path.join(HERE, f), os.path.join(DEST, f))
    for f in OLD_FILES:
        if os.path.exists(os.path.join(DEST, f)):
            os.remove(os.path.join(DEST, f))
    say("copied the tool to %s" % DEST)

    pairs = targets(shells)
    if not pairs:
        say("no shell found to hook into. Run again with --shell bash, zsh or pwsh.")
    for shell, path in pairs:
        try:
            add_line(path, hook_line(shell))
            say("%s: added one line to %s" % (shell, path))
        except OSError as e:
            say("%s: could not change %s (%s). Add this line to it yourself:" % (shell, path, e.strerror))
            say("    " + hook_line(shell))

    data, indent = read_settings()
    if data is None:
        say("left %s alone: it is not valid JSON. The status line and the account hook are optional."
            % SETTINGS)
    else:
        before = json.dumps(data, sort_keys=True)
        current = (data.get("statusLine") or {}).get("command", "")
        if current and not is_ours(current):
            say("kept your own Claude status line. To use the Hats one, set statusLine.command to: %s" % STATUS_CMD)
        elif current != STATUS_CMD:
            data["statusLine"] = {"type": "command", "command": STATUS_CMD}
            say("turned on the account status line in %s" % SETTINGS)
        data, added = with_context(data)
        if not added:
            say("left the hooks in %s alone: \"hooks\" is not in the usual form." % SETTINGS)
        if json.dumps(data, sort_keys=True) != before:
            try:
                if os.path.exists(SETTINGS) and not os.path.exists(SETTINGS + ".pre-hats.bak"):
                    shutil.copy2(SETTINGS, SETTINGS + ".pre-hats.bak")
                write_settings(data, indent)
                say("Claude now starts each session knowing which account it runs on")
            except OSError as e:
                say("could not change %s (%s); the status line and account hook are optional."
                    % (SETTINGS, e.strerror))

    with open(os.path.join(DEST, "install.json"), "w", encoding="utf-8") as f:
        json.dump({"repo": HERE, "shells": shells or [], "python": PY}, f, indent=2)

    print("""
Done. Open a new terminal, then:

  hat add work you@company.example   create a profile for another account
  hat login work                     sign it in (opens the browser)
  hat map work ~/code/company        use it automatically in that folder
  hat                                menu to switch by hand (also F2)

Your current Claude login stays as the profile "personal". Run `hat help` for more.""")


# ------------------------------------------------------------------ uninstall

def purge_profiles():
    """Sign out every profile in ~/.claude-profiles and delete them. Links inside are
    removed as links (hat.remove_profile_dir), so nothing shared is deleted."""
    sys.path.insert(0, HERE)
    import hat
    if not os.path.isdir(PROFILES):
        return
    claude = shutil.which("claude")
    for name in os.listdir(PROFILES):
        folder = os.path.join(PROFILES, name)
        if claude and os.path.isdir(folder):
            # Clears the login wherever Claude keeps it (on macOS: the Keychain).
            subprocess.run([claude, "auth", "logout"], env=dict(os.environ, CLAUDE_CONFIG_DIR=folder),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        hat.remove_profile_dir(folder)
    os.rmdir(PROFILES)


def uninstall(purge):
    print("Removing Hats")
    candidates = [os.path.join(HOME, n) for n in (".bashrc", ".bash_profile", ".bash_login", ".profile", ".zshrc")]
    for path in candidates + powershell_profiles():
        try:
            if strip_marker(path):
                say("removed the line from %s" % path)
        except OSError as e:
            say("could not change %s (%s). Remove the line ending in '%s' yourself." % (path, e.strerror, MARKER))

    data, indent = read_settings()
    if data:
        changed = False
        if is_ours((data.get("statusLine") or {}).get("command", "")):
            del data["statusLine"]
            changed = True
        data, removed = without_context(data)
        if changed or removed:
            try:
                write_settings(data, indent)
                say("removed the status line and account hook from %s" % SETTINGS)
            except OSError as e:
                say("could not change %s (%s). Remove the Hats statusLine and SessionStart hook yourself."
                    % (SETTINGS, e.strerror))

    for f in FILES + OLD_FILES + ["install.json"]:
        if os.path.exists(os.path.join(DEST, f)):
            os.remove(os.path.join(DEST, f))
    say("removed the tool from %s" % DEST)

    if purge:
        print("\nThis signs out and deletes every profile in %s, and deletes %s\n"
              "(your profile list and folder rules). ~/.claude and your main login are not touched."
              % (PROFILES, DEST))
        if input("Delete them? [y/N] ").strip().lower().startswith("y"):
            purge_profiles()
            if os.path.islink(DEST):
                os.remove(DEST)
            else:
                shutil.rmtree(DEST, ignore_errors=True)
            say("deleted them")
        else:
            say("kept them")
    else:
        say("kept your profiles (%s) and settings (%s)." % (PROFILES, os.path.join(DEST, "hats.conf")))
        say("To delete those too: python3 install.py --uninstall --purge")
    print("\nDone. Terminals that are already open keep Hats until you close them.")


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return
    shells = None
    if "--shell" in argv:
        i = argv.index("--shell")
        if i + 1 >= len(argv):
            sys.exit("--shell needs a value, e.g. --shell zsh")
        shells = [s.strip() for s in argv[i + 1].split(",") if s.strip()]
        bad = [s for s in shells if s not in SHELLS]
        if bad:
            sys.exit("unknown shell '%s' (use bash, zsh or pwsh)" % bad[0])
    if "--uninstall" in argv:
        uninstall("--purge" in argv)
    else:
        install(shells)


if __name__ == "__main__":
    main(sys.argv[1:])
