# Changelog

What changed in each version of Hats. `hat version` shows yours; `hat update` gets
the latest.

## 1.0.0 — 2026-11-25

First public release.

- **Profiles:** one Claude Code login per account, side by side (`CLAUDE_CONFIG_DIR`),
  sharing settings, history and memory through links to `~/.claude`.
- **Always visible:** the account name in its own colour at the start of the prompt,
  in the terminal tab title, and in Claude Code's status line. Claude itself is told
  its account at the start of each session.
- **Choosing the account:**
  - by folder with `hat map`;
  - by hand per terminal with `hat` / F2 or `hat use`;
  - one-off with `hat run`.
- **Wrong-account guard:** `claude` refuses to start on a profile signed in with an
  unexpected email, and `hat login` signs such a login straight back out.
- `hat add <name> --separate`: an account that keeps its own history and memory.
- `hat remove`, `hat doctor [--fix]`, `hat status [--json]`, `hat update`,
  `hat export` / `hat import`, `hat code` (VS Code, Cursor, Windsurf).
- A warning when an account has used 90% or more of its 5-hour or weekly limit.
- **Platforms:**
  - Linux (bash), tested;
  - macOS (zsh, bash) and Windows (PowerShell 7 and 5.1), new.
  
  All logic is in `hat.py`: Python 3.8+, standard library only.
- `install.py` installs, updates and uninstalls on every platform. It keeps
  start-up files and `settings.json` exactly as they were apart from its own lines.
