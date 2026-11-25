# Hats for Claude Code

**Wear the right Claude account for every project.**

Use several Claude accounts on one computer, see at a glance which one is active,
and switch in one keypress instead of logging out and back in. The command is `hat`.
The name comes from "wearing many hats": one person, several roles.

![Hats in a terminal: the prompt shows the account, cd switches it, F2 picks one by hand](docs/demo.gif)

## Why

Many developers have more than one Claude account: a personal one, one from their
employer, sometimes one per client. Each company may require that its code is
only ever worked on with *its* account, for billing, for data agreements, or for
admin controls.

Claude Code has one login per computer, so working on two companies' projects in
a day means `/logout`, `/login`, a browser round trip, and remembering to switch
back. Forgetting is easy and invisible: nothing on screen tells you which account
a terminal is using until you check.

Hats fixes both problems:

- **Every account stays signed in.** Each one gets its own login, kept side by side,
  so switching takes no browser trip.
- **You always see which account is active.** The account name sits at the start of
  your prompt, in the terminal tab title, and in Claude Code's status line.
- **The right account is picked for you.** Map a folder to an account once; every
  `claude` started in that folder uses it.
- **The wrong account can't slip through.** If an account is signed in with an
  unexpected email, `claude` refuses to start on it, and `hat login` signs it straight
  back out.
- **Claude knows too.** Each session starts with a note telling Claude which account
  it runs on.
- **You can still choose by hand.** Press F2 (or type `hat`) for a menu.
- **Nothing else changes.** Settings, history, memory, `--resume` and permissions are
  shared by all accounts, so Claude behaves the same whichever account it runs on.

## What you see

```
personal you@laptop:~$                          the account `claude` would use here
work you@laptop:~/code/acme-app$                chosen by a folder rule
personal · pinned you@laptop:~/code/acme-app$   picked by hand for this terminal
```

- Each account has its own colour.
- **Grey** means that account is not signed in yet.
- **`⚠` in red** means it is signed in with a different email than expected.

Inside Claude Code the status line shows the account, the model, and how much of
the context and the account's limits are used:

```
work  Acme · Team  │  Opus 5.5 · high  │  context 20% · 5h 7% · week 74%
```

## Platforms

| Platform | Shell | Status |
| --- | --- | --- |
| Linux | bash | Tested |
| Windows with WSL | bash (install inside WSL) | Same as Linux |
| macOS | zsh (the default) or bash | New, not yet tried on a Mac |
| Windows | PowerShell 7 or Windows PowerShell 5.1 | New, not yet tried on Windows |

If something looks wrong on your platform, open an issue with what you saw.

**Requirements:** Claude Code, and Python 3.8 or newer.
- **Linux:** Python is already installed.
- **macOS:** Python comes with the Xcode command line tools, which `git` also needs.
- **Windows:** install it with `winget install Python.Python.3.12`.

## Install

macOS, Linux, WSL:

```bash
git clone <repo-url> hats-for-claude-code
cd hats-for-claude-code
python3 install.py
```

Windows (PowerShell):

```powershell
git clone <repo-url> hats-for-claude-code
cd hats-for-claude-code
python install.py
```

Open a new terminal afterwards. Your existing Claude login becomes the profile
`personal` and stays the default, so nothing changes until you add an account.

The installer finds your shells and hooks into each one. To choose yourself, pass
`--shell bash`, `--shell zsh`, `--shell pwsh`, or several: `--shell zsh,pwsh`.

**Windows:** if PowerShell says running scripts is disabled, allow your own
profile script once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

To update: `git pull`, then run the installer again.

## Add an account

Say you also work for a company called Acme, with its own Claude account:

```bash
hat add work you@acme.example        # 1. create a profile; the email is optional
hat login work                       # 2. sign it in (opens the browser)
hat map work ~/code/acme             # 3. optional: use it automatically in that folder
```

1. **Add** creates the profile. With an email, Hats warns if the profile is ever signed in as someone else.
2. **Login** opens the browser. Sign in with that account and approve. If your browser
   is already signed in to claude.ai as another account, sign out there first, or paste
   the login link into a private window.
3. **Map** is optional. Every `claude` started in `~/code/acme` or below then uses `work`.
   Without a rule, you switch by hand.

Add as many as you need, for example one per client: `hat add client-a`,
`hat add client-b`.

**Keeping a client's work fully apart.** By default all accounts share history and
memory, so `claude --resume` works the same everywhere. If a client requires that
nothing from their sessions is visible to other accounts, add it as separate:

```bash
hat add client-a you@client-a.example --separate
```

That account then keeps its own history and memory. Settings, `CLAUDE.md`,
commands and agents are still shared.

## Remove an account

```bash
hat remove work
```

This signs the profile out on this computer, deletes its folder
(`~/.claude-profiles/work`) and its folder rules. It asks first; add `--yes` to
skip the question. Your shared history, memory and settings stay.

The main login (`personal`, in `~/.claude`) is never removed. You can't remove
the default profile either: make another one the default first with
`hat default <name>`.

## Daily use

```bash
claude                    # starts Claude on the account shown in the prompt
hat                       # menu: pick the account for this terminal (also F2)
hat use work              # same, without the menu
hat auto                  # stop picking by hand; follow the folder again
hat status                # every account: email, team, plan, usage, folder rules
```

**Pinned** means you picked the account by hand for this terminal window. It
stays on that account in every folder until you choose `auto`. Other windows are
not affected.

A running Claude session keeps the account it started with. To move a
conversation to another account: exit, switch, then `claude --continue`.

When an account has used 90% or more of its 5-hour or weekly limit, `claude`
says so before starting.

Other commands:

```bash
hat map <profile> [dir]   # always use a profile in a folder (default: current folder)
hat unmap [dir]           # remove that rule
hat default <profile>     # the profile for folders without a rule
hat run <profile> [args]  # one-off: start claude on a profile without switching
hat exec <profile> <cmd>  # start any program on a profile
hat code <profile> [dir]  # open VS Code on a profile (also --editor cursor or windsurf)
hat doctor [--fix]        # check the setup; --fix repairs broken links
hat update                # get the latest version from git and reinstall
hat export [file]         # save profiles and folder rules (no logins) to a file
hat import <file>         # add them on another computer
hat status --json         # status for scripts
hat style <clean|badge|minimal>   # how the prompt shows the account
hat edit                  # open the settings file
hat help
```

## Editors (VS Code, Cursor, Windsurf)

The Claude extension in an editor uses the account the editor was started with.
Editors reuse a window that is already open, so `hat code` opens a separate window
for the account. Your extensions are shared; that window keeps its own editor
settings and recent files.

```bash
hat code work ~/code/acme                 # VS Code
hat code work ~/code/acme --editor cursor # Cursor
```

This is new and not yet tried with every editor.

## A new computer

```bash
hat export ~/hat-setup.json      # on the old computer: profiles, emails, folder rules
hat import ~/hat-setup.json      # on the new one, after installing hat
hat login work                   # then sign in to each account
```

The file never contains logins. Profiles and rules that already exist on the new
computer are left as they are.

## When something is wrong

```bash
hat doctor
```

It checks Claude Code, the shell hook, every profile's links and sign-in, the folder
rules, and the status line, and says how to fix each problem. `hat doctor --fix`
repairs broken links by itself.

## Uninstall

```bash
python3 install.py --uninstall            # remove Hats; profiles and their logins stay
python3 install.py --uninstall --purge    # also delete all profiles and their logins
```

On Windows use `python` instead of `python3`. Uninstalling removes everything the
installer added (see below). Terminals that are already open keep Hats until you
close them. Your main Claude login in `~/.claude` is never removed.

## How it works

Claude Code stores its login in a config folder, `~/.claude` by default. The
`CLAUDE_CONFIG_DIR` environment variable tells it to use another folder instead.
Hats gives each account its own folder and sets that variable for you.

```
~/.claude/                     personal   (the standard folder, untouched)
~/.claude-profiles/work/       work       (its own login; everything else links to ~/.claude)
~/.claude-profiles/client-a/   client-a
```

When you type `claude`, Hats:

1. works out the profile: a pin for this terminal, else the closest mapped folder,
   else the default;
2. starts the real Claude Code with `CLAUDE_CONFIG_DIR` pointing at that profile's
   folder (or unset, for `personal`).

A profile folder holds only what belongs to the account. The rest is a link back
to `~/.claude`, so all accounts share it:

| Per account | Shared by all accounts |
| --- | --- |
| the login (`.credentials.json`, or a Keychain entry on macOS) | `settings.json`, `CLAUDE.md`, `keybindings.json` |
| `.claude.json` (account details, per-project state) | `projects/` (history and memory), `history.jsonl` |
| `plugins/`, `skills/` (synced from each account) | `commands/`, `agents/`, `plans/`, `tasks/`, file history |

On Windows, shared folders are junctions (no admin rights needed) and shared files
are symlinks when Developer Mode is on, hard links otherwise.

A new profile starts with your folder trust and permission choices copied from
the main config, so Claude doesn't ask again for projects you already trust. It
never copies the account itself.

Inside a Claude Code session the `claude` wrapper steps aside, so anything Claude
runs keeps the account of the session it came from.

On Linux and macOS, Hats hands the terminal over to Claude Code once it has set the
account, so Ctrl-C, Ctrl-Z and exit codes behave as if you had started Claude
directly. If Hats is missing (for example after uninstalling while a terminal was
open), `claude` is simply the normal command again.

**If you already set `CLAUDE_CONFIG_DIR` yourself**, Hats keeps it: on first use,
that folder becomes the profile `personal` and is what other profiles share
(the `base` line in the settings file).

### The code

| File | What it is |
| --- | --- |
| `hat.py` | All the logic: profiles, folder rules, the menu, the prompt marker, the status line, doctor, export/import. Python standard library only. |
| `hat.bash`, `hat.zsh`, `hat.ps1` | Small hooks that put the marker in the prompt, wrap `claude`, add F2 and tab completion. |
| `install.py` | Installs, updates and uninstalls on every platform. |
| `tests/` | Automated tests (see Development). |

Settings live in `~/.config/hats/hats.conf` (`hat edit`). It is plain text, the same
on every platform:

```
default personal
style clean
profile personal native
profile work     ~/.claude-profiles/work      you@acme.example
profile client-a ~/.claude-profiles/client-a
dir work     /home/you/code/acme
dir client-a C:\Users\you\code\client-a
```

`native` means the standard `~/.claude`. The longest matching folder rule wins,
and a pin beats every rule. Folders may contain spaces; the email, if any, is the
last word on a `profile` line and is matched without regard to upper/lower case.

## What it changes on your computer

The installer touches three things, and `--uninstall` takes all three out again:

| What | Change |
| --- | --- |
| `~/.config/hats/` | The tool's files, settings and a small cache. |
| Shell start-up files (`~/.bashrc`, `~/.zshrc`, on macOS bash's login file, or the PowerShell `$PROFILE`) | One line, ending in `# hats: Claude Code accounts`. The rest of the file is kept byte for byte. |
| `~/.claude/settings.json` | Sets `statusLine`, only if you don't have one, and adds one `SessionStart` hook that tells Claude its account. Your own hooks stay as they are. The file keeps its formatting; a backup goes to `settings.json.pre-hats.bak`. If the file isn't valid JSON, it is left alone. |

Using it creates `~/.claude-profiles/<name>` for each account you add.

Backups Hats makes are left in place after uninstalling, for you to delete when you
like: `settings.json.pre-hats.bak`, and `*.hats-bak-<date>` files (made when one
profile saved a shared file and Hats copied it back to the shared copy).

Hats never:
- changes or signs out your main login;
- deletes anything in `~/.claude`;
- replaces a file of yours that is a symlink (for example a dotfiles link).

Removing a profile deletes its links, never what they point to.

## Troubleshooting

- **The prompt shows `⚠` and "wrong account".** The browser approved a different
  Claude account. Sign out of claude.ai in the browser (or use a private window), then
  `hat login <profile>` again.
- **I need plain Claude for a moment.** `command claude` in bash/zsh skips Hats. In
  PowerShell, run `claude.exe` (or `claude.cmd` if Claude Code came from npm).
- **Usage numbers are missing for an account.** They come from Claude Code itself and
  appear after the first Claude session on that account.
- **zsh:** Hats turns on `PROMPT_SUBST` (needed to show the name; most themes already do)
  and binds F2. If you use F2 for something else, remove the `bindkey` lines from
  `~/.config/hats/hat.zsh`.
- **macOS:** on a Mac, Claude Code keeps the login in the Keychain rather than a file,
  so Hats can't tell whether a saved login has expired. The name may stay in colour
  until Claude asks you to sign in again.

## More

- [`examples/`](examples/): a commented settings file and an example export.
- [`CHANGELOG.md`](CHANGELOG.md): what changed in each version (`hat version` shows yours).
- [`AGENTS.md`](AGENTS.md): how the code fits together and the rules it keeps. Read it
  before changing or forking Hats; AI coding tools read it automatically.
- [`LICENSE`](LICENSE): MIT.

## Development

```bash
python3 -m unittest discover -s tests
```

The tests run every command, the installer and the bash hook against a temporary
home folder with a stand-in `claude`, so they never touch your real setup. They
run on Linux and macOS.

To remake the demo after changing the look: `python3 docs/make_demo.py` (needs
Pillow).
