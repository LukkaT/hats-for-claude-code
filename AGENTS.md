# AGENTS.md

Guide for anyone changing Hats: people, and AI coding agents (Claude Code reads it
through `CLAUDE.md`). Read this before editing. For what the tool does from a user's
point of view, see `README.md`.

## What Hats is

A way to use several Claude Code accounts on one computer. Each account is a
**profile**: its own Claude Code config folder, chosen with the `CLAUDE_CONFIG_DIR`
environment variable. The shell shows the active profile and picks it by folder;
everything except the login is shared through links to `~/.claude`.

Its purpose is narrow: **you can always see which account is active, and the wrong
account cannot be used by accident.** Features that work against that do not belong
here.

Automatic switching (1.2.0) is allowed only on these terms:
- the owner turns it on in `hat settings`;
- it moves only between accounts the owner put in the order;
- it always says what it did;
- it asks before moving a chat that is already running.

An account outside the order is never switched to or from.

## Layout

| Path | Role |
| --- | --- |
| `hat.py` | All logic. One file, Python 3.8+, standard library only. |
| `hat.bash`, `hat.zsh`, `hat.ps1` | Thin shell hooks: prompt marker, `claude` wrapper, `hat` function, F2, completion. No logic. |
| `install.py` | Install, update, uninstall, purge on every platform. Imports `hat.py` for safe folder removal. |
| `tests/test_hat.py` | Tests. Run them before and after every change. |
| `docs/make_demo.py` | Draws `docs/demo.gif` (needs Pillow; not a Hats dependency). |
| `docs/make_settings_demo.py` | Draws `docs/settings.gif`, the automatic-switching walkthrough, with the same look. |
| `docs/settings.md` | The full guide to `hat settings` and automatic switching. Keep it in step with the code. |
| `examples/` | Example settings file and export. |
| `CHANGELOG.md` | One entry per version. |

## How the pieces talk

- **Hooks → `hat.py`.** Hooks call `python hat.py [--shell bash|zsh|pwsh] [--eval] <command> [args]`.
- **Changing the terminal's environment.** Only `pick`, `use` and `auto` change the
  terminal. They run with `--eval`:
  - stdout carries shell code only (`export …` / `$env:… = …`), which the hook evaluates;
  - all text for people goes to stderr.
  
  Never print anything else to stdout in `--eval` mode.
- **`prompt`** prints `<marker>\x1f<tab title>`. Escape codes in the marker are wrapped
  for the shell's line editor by `hide()`: `\001…\002` for bash, `%{…%}` for zsh, nothing
  for PowerShell. For bash the title escape is already inside the marker.
- **`statusline` and `context`** are run by Claude Code itself, from
  `~/.claude/settings.json` (`statusLine` and a `SessionStart` hook). They find the
  profile from the `CLAUDE_CONFIG_DIR` they inherit. `context` must print plain text,
  not JSON: Claude Code adds plain stdout from a SessionStart hook to Claude's context.
- **`claude`** resolves the profile, then on Linux and macOS replaces itself with Claude
  Code (`os.execve`), so signals and exit codes are Claude's own. On Windows it waits
  with Ctrl-C ignored.
- **Automatic switching** (`takeover`, `run_chat`):
  - At start, a profile in the order with less than `switch_left`% of a limit left gives way to the first
    profile in the order with room left.
  - When switching is on and the profile is in the order, a chat is *watched*: Hats
    waits for Claude (Ctrl-C ignored, as on Windows) instead of `execve`, and sets
    `HAT_RUN`.
  - The status line writes the chat's `session_id` to `runs/<HAT_RUN>`.
  - After Claude exits with the profile low, Hats asks, then runs `claude --resume <id>` on
    the next profile. Chats are in the shared `projects/`; a `--separate` profile
    can't take part.
- **Profile resolution** (`Config.resolve`): `HAT_PIN` (a pin in this terminal) → the
  longest matching `dir` rule → `default`.

## Rules that must not be broken

These protect other people's computers. Each has a test; keep it that way.

1. **Never delete or rewrite what a link points to.**
   - Profile folders are removed with `remove_profile_dir`, which unlinks links.
   - `is_link` treats any Windows reparse point as a link. Python before 3.12 reports a
     junction as a plain folder.
   - Never use `shutil.rmtree` on a profile folder.
2. **Never touch the main login.**
   - `~/.claude` and `~/.claude.json` are only read, except for creating the shared
     folders if they are missing.
   - `hat remove` refuses the `native` profile and the default.
3. **Start-up files keep every byte that isn't Hats's line**: encoding (UTF-16 PowerShell
   profiles included), byte-order mark, line endings. Use `read_lines` / `write_lines` in
   `install.py`.
4. **Files that are symlinks stay symlinks.** Write through `os.path.realpath`, or copy
   contents (see `write_atomic`, `write_settings`, the shared-file merge in `ensure_links`).
5. **`settings.json`:**
   - keep its indent and non-ASCII text;
   - leave it alone if it isn't valid JSON;
   - only ever add or remove Hats's own `statusLine` and its own `SessionStart` entry
     (`is_ours`, `is_our_context`).
6. **`claude` keeps working when Hats is broken.** Hooks fall back to the plain command
   when Python or `hat.py` is missing. Unexpected errors print how to bypass Hats.
7. **Only manage folders Hats created.** Links are made only inside
   `~/.claude-profiles/<name>` (`Config.managed`). A folder a user points a profile at
   is used as it is.
8. **No logins in exports, caches or messages** beyond the email and organisation name.

## Constraints

- **Python 3.8+, standard library only.** No third-party packages for Hats itself.
- **The prompt path is hot.** `prompt` runs before every prompt:
  - no subprocesses;
  - no parsing of large files without the mtime cache in `info()`;
  - keep it near 20 ms on Linux.
- **Shell compatibility:**
  - `hat.bash` must run on bash 3.2 (macOS's built-in bash);
  - `hat.ps1` must run on Windows PowerShell 5.1: no `??`, no ternary, use `[char]27` not `` `e ``.
- **Hooks stay thin.** If a hook needs logic, put it in `hat.py`.
- **Messages:**
  - errors start with `hat: ` and say how to fix the problem;
  - plain words, as a person would say them;
  - raise `Fail(message)` for anything the user can act on (exit code 2).

## Testing

```bash
python3 -m unittest discover -s tests
```

- Each test runs `hat.py` / `install.py` as a separate process, with `HOME` set to a
  temporary folder.
- A stand-in `claude` on `PATH` logs how it was called. `auth login` signs in as
  `$FAKE_EMAIL`, and `auth logout` removes the credentials.
- A stand-in `code` editor does the same for `hat code`.
- Nothing touches the real machine. The tests run on Linux and macOS.

Add a test with every change, and for every bug fixed.

### Not yet run anywhere

Treat these as unverified and ask for reports:
- `hat.zsh` and `hat.ps1` in real shells;
- macOS (Keychain-based login detection);
- Windows (junctions, hard links, PowerShell profiles, `msvcrt` key reading);
- `hat code` with real editors.
- carrying a chat over with real Claude Code (`claude --resume <id>` on another
  profile, `session_id` in the status-line input).

## Adding a command

1. Write `cmd_<name>(cfg, args, emit)` in `hat.py` and add it to `COMMANDS`.
2. Add it to `HELP`, and to tab completion in `hat.bash` (`compgen -W …`) and `hat.zsh`
   (`compadd …`).
3. If it changes the terminal's environment, it must use `emit` and be routed through
   `--eval` in all three hooks.
4. Document it in `README.md`, add tests, add a line to `CHANGELOG.md`.

## Changing what Claude Code stores

Hats reads Claude Code's own files, and these can change between Claude Code versions:
- `.claude.json` (`oauthAccount`);
- `.credentials.json` (`claudeAiOauth`);
- on macOS, Keychain entries named per config folder.

If sign-in states look wrong after a Claude Code update, check `login_of()` first.

## Releasing

1. Bump `VERSION` in `hat.py`.
2. Add a dated section to `CHANGELOG.md`.
3. If the look changed, run `python3 docs/make_demo.py` (and `docs/make_settings_demo.py`
   for the settings screen) and commit the new GIF.
4. Users get it with `hat update` (git pull plus reinstall).

## Privacy in this repository

Docs, examples, tests and the demo use made-up names only: `personal`, `work`,
`client-a`, `acme.example`. Never commit real names, emails, company names or paths.
