# How Hats works

## The idea

Claude Code stores its login in a config folder, `~/.claude` by default. The
`CLAUDE_CONFIG_DIR` environment variable tells it to use another folder instead.
Hats gives each account its own folder and sets that variable for you.

```
~/.claude/                     personal   (the standard folder, left as it is)
~/.claude-profiles/work/       work       (its own login; everything else links to ~/.claude)
~/.claude-profiles/client-a/   client-a
```

When you type `claude`, Hats:

1. **works out the account:** a pin for this terminal; otherwise the closest mapped
   folder; otherwise the default;
2. **starts the real Claude Code** with `CLAUDE_CONFIG_DIR` pointing at that account's
   folder, or unset for `personal`.

On Linux and macOS, Hats then hands the terminal over to Claude Code completely, so
Ctrl-C, Ctrl-Z and exit codes behave as if you had started Claude directly.

Inside a Claude Code session, the `claude` wrapper steps aside. Anything Claude
runs keeps the account of the session it came from.

## What is shared

An account's folder holds only what belongs to that account. Everything else is a
link back to `~/.claude`, so all accounts share it:

| Per account | Shared by all accounts |
| --- | --- |
| the login (`.credentials.json`, or a Keychain entry on macOS) | `settings.json`, `CLAUDE.md`, `keybindings.json` |
| `.claude.json` (account details, per-project state) | `projects/` (history and memory), `history.jsonl` |
| `plugins/`, `skills/` (synced from each account) | `commands/`, `agents/`, `plans/`, `tasks/`, file history |

- **A `--separate` account** keeps `projects/`, `history.jsonl`, file history, plans,
  tasks and todos to itself. Settings, `CLAUDE.md`, commands and agents stay shared.
- **On Windows**, shared folders are junctions, which need no admin rights. Shared files
  are symlinks when Developer Mode is on, and hard links otherwise.
- **A new account** starts with your folder-trust and permission choices copied from
  the main config, so Claude doesn't ask again about projects you already trust.
  The login itself is never copied.
- **If you already set `CLAUDE_CONFIG_DIR` yourself**, Hats keeps it. On first use,
  that folder becomes the account `personal` and is what other accounts share (the
  `base` line in the settings file).

Because chats are in the shared `projects/`, automatic switching (`hat settings`) can
continue a chat on another account with `claude --resume`. It does this only between
accounts that aren't `--separate`.

## The settings file

`~/.config/hats/hats.conf` (open it with `hat edit`) is plain text, the same on every
platform. A fully commented example is in [`examples/hats.conf`](../examples/hats.conf).

```
default personal
style clean
profile personal native
profile work     ~/.claude-profiles/work      you@acme.example
profile client-a ~/.claude-profiles/client-a
dir work     /home/you/code/acme
dir client-a C:\Users\you\code\client-a
```

- **`native`** means the standard `~/.claude`.
- **The longest matching folder rule wins**, and a pin beats every rule.
- **Spaces in folder names are fine.**
- **The email** is the last word on a `profile` line, if there is one. Upper and lower
  case don't matter.

## Editors

The Claude extension in VS Code, Cursor or Windsurf uses the account the editor was
started with. Editors reuse a window that is already open, so `hat code` opens a
separate window for the account. Your extensions are shared; that window keeps its
own editor settings and recent files.

## A new computer

```bash
hat export ~/hats-setup.json      # on the old computer: accounts, emails, folder links
hat import ~/hats-setup.json      # on the new one, after installing Hats
hat login work                    # then sign in to each account
```

The file never contains logins. Accounts and links that already exist on the new
computer are left as they are.

## What the installer changes on your computer

The installer changes three things, and `python3 install.py --uninstall` takes all
three out again:

| What | Change |
| --- | --- |
| `~/.config/hats/` | The tool's files, settings and a small cache. |
| Your shell's start-up file: `~/.bashrc`, `~/.zshrc`, on macOS bash's login file, or the PowerShell `$PROFILE` | Adds one line ending in `# hats: Claude Code accounts`. The rest of the file is kept byte for byte. |
| `~/.claude/settings.json` | Adds the status line (only if you have none) and one `SessionStart` hook that tells Claude its account. Your own hooks stay as they are, and the file keeps its formatting. A backup goes to `settings.json.pre-hats.bak`. If the file isn't valid JSON, it is left alone. |

- **New folders:** each account you add creates `~/.claude-profiles/<name>`.
- **Backups:** these are left in place after uninstalling, for you to delete:
  - `settings.json.pre-hats.bak`;
  - `*.hats-bak-<date>` files, made when one account saved a shared file and Hats copied
    it back to the shared copy.

Hats never:
- changes or signs out your main login;
- deletes anything in `~/.claude`;
- replaces a file of yours that is a symlink, such as a dotfiles link.

Removing an account deletes its links, never what they point to.

## The code

| File | What it is |
| --- | --- |
| `hat.py` | All the logic. Python standard library only. |
| `hat.bash`, `hat.zsh`, `hat.ps1` | Small shell hooks: the name in the prompt, the `claude` wrapper, F2, tab completion. |
| `install.py` | Install, update and uninstall on every platform. |
| `tests/` | Automated tests: `python3 -m unittest discover -s tests`. |
| `docs/make_demo.py` | Draws `docs/demo.gif` (needs Pillow). |

The rules every change must keep are in [AGENTS.md](../AGENTS.md).
