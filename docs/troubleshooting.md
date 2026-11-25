# Troubleshooting

Start with:

```bash
hat doctor
```

It checks:
- Claude Code;
- the shell hook in this terminal;
- every account's sign-in and links;
- your folder rules;
- the status line.

For each problem it says how to fix it. `hat doctor --fix` repairs broken links itself.

## Common problems

**The prompt doesn't show an account name.**
Open a new terminal; the installer's change takes effect there. If it still doesn't
appear, run the installer again from the downloaded folder: `python3 install.py`.

**The name is grey.**
That account isn't signed in. Run `hat login <name>`.

**The name is red with `⚠`, or `claude` says "not starting Claude".**
The account is signed in with a different email than the one you gave it. Usually
the browser approved the wrong Claude account. To fix it:
1. Sign out of claude.ai in the browser, or use a private window.
2. Run `hat login <name>` again.

**`hat login` opened the wrong account.**
Same cause, and the same fix. Hats signs a wrong login straight back out, so it
can't be used by mistake.

**I need plain Claude for a moment, without Hats.**
- **bash or zsh:** type `command claude`.
- **PowerShell:** type `claude.exe`, or `claude.cmd` if Claude Code was installed with npm.

**Usage numbers are missing for an account.**
They come from Claude Code itself and appear after the first Claude session on that
account.

**F2 does something else in my terminal.**
In zsh, remove the `bindkey` lines from `~/.config/hats/hat.zsh`; in bash, remove the
`bind` lines from `~/.config/hats/hat.bash`. You can always type `hat` instead.

**zsh: my prompt theme changed.**
Hats turns on `PROMPT_SUBST`, which it needs to show the name. Most themes already
turn it on.

**macOS: the name stays in colour although Claude asks me to sign in.**
On a Mac, Claude Code keeps the login in the Keychain, so Hats can't tell when a saved
login has expired. Sign in when Claude asks, or run `hat login <name>`.

**Windows: "running scripts is disabled on this system".**
Allow your own PowerShell profile to run, once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**Still stuck?**
[Open an issue](https://github.com/LukkaT/hats-for-claude-code/issues) and include the
output of `hat doctor`. It shows account names and emails, so remove anything you'd
rather not share.
