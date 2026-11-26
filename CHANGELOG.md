# Changelog

What changed in each version of Hats. `hat version` shows yours; `hat update` gets
the latest.

## 1.2.0 — 2026-11-26

- **Automatic switching**, off until you turn it on in the new **`hat settings`**
  screen. You choose when an account counts as low (less than 5% to 50% left of its
  5-hour or weekly limit) and which accounts take turns, in which order.
  - `claude` starts on the next account that takes turns when the one in use is low,
    and says so.
  - A running chat moves by itself: when a task finishes and the account is low, Hats
    reopens the same chat on the next account (`claude --resume`). If the limit runs
    out in the middle of a task, the task continues there ("Continue where you
    stopped"). The status line says `low: moves to <account> after this task`.
  - The installer adds two Hats hooks to Claude Code's settings for this (`Stop`,
    `StopFailure`); they do nothing while switching is off.
  - Accounts under "Never switch to or from" are never switched to or from.
  - A "Now:" line on the screen says in plain words what will happen.
  - `hat settings switch on|off`, `level <% left>` and `order <accounts>` do the same
    from scripts.
- `hat status` says whether switching is on, and `hat status --json` has `switching`.
- The warning near a limit says how much is left ("has 7% left"), like `hat status`.
- Guide: `docs/settings.md`, with a click-to-open walkthrough of every step
  (`docs/settings/step-N.png`). Overview animation: `docs/settings.gif`. Both are
  drawn by `docs/make_settings_demo.py`.

## 1.1.0 — 2026-11-25

- `hat status` and the F2 menu show how much of each account's 5-hour and weekly
  limits is **left**, and when each resets, on a line under the account. Accounts
  without usage data yet say so.
- `hat status --json`: `left_5h`, `left_week`, `resets_5h`, `resets_week` replace
  `usage_5h` and `usage_week`.
- A smoother, clearer demo animation.

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
