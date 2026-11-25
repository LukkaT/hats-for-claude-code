"""Tests for hat. Each test runs hat.py / install.py as a separate process with HOME
pointed at a temporary folder and a stand-in `claude` program on PATH, so nothing on
the real machine is read or changed.

Run from the repository folder:  python3 -m unittest discover tests
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAT = os.path.join(REPO, "hat.py")
INSTALL = os.path.join(REPO, "install.py")

# Stands in for Claude Code: records how it was called, and fakes `auth login/logout`.
FAKE_CLAUDE = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys
    d = os.environ.get("CLAUDE_CONFIG_DIR", "")
    with open(os.path.join(os.environ["HOME"], "claude-calls.log"), "a") as f:
        f.write(json.dumps({"dir": d, "args": sys.argv[1:]}) + "\\n")
    if os.environ.get("FAKE_STATUS") and "--resume" not in sys.argv:
        # Claude Code runs the status line during a chat: it reports the limits and the chat's id.
        import subprocess
        subprocess.run([sys.executable, os.environ["FAKE_HAT"], "statusline"],
                       input=os.environ["FAKE_STATUS"], text=True, capture_output=True)
    if sys.argv[1:3] == ["auth", "logout"] and d:
        for name in (".credentials.json",):
            p = os.path.join(d, name)
            if os.path.exists(p):
                os.remove(p)
    if sys.argv[1:3] == ["auth", "login"] and d:
        # The "browser" signs in as FAKE_EMAIL.
        with open(os.path.join(d, ".claude.json"), "w") as f:
            json.dump({"oauthAccount": {"emailAddress": os.environ["FAKE_EMAIL"]}}, f)
        with open(os.path.join(d, ".credentials.json"), "w") as f:
            json.dump({"claudeAiOauth": {"accessToken": "t"}}, f)
""")

# Stands in for an editor: records its arguments and the account it was given.
FAKE_EDITOR = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys
    with open(os.path.join(os.environ["HOME"], "editor-calls.log"), "a") as f:
        f.write(json.dumps({"dir": os.environ.get("CLAUDE_CONFIG_DIR", ""), "args": sys.argv[1:]}) + "\\n")
""")


@unittest.skipIf(os.name == "nt", "these tests use POSIX shells and symlinks")
class HatTest(unittest.TestCase):

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="hats-test-")
        bin_dir = os.path.join(self.home, "bin")
        os.makedirs(bin_dir)
        fake = os.path.join(bin_dir, "claude")
        with open(fake, "w") as f:
            f.write(FAKE_CLAUDE)
        os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
        editor = os.path.join(bin_dir, "code")
        with open(editor, "w") as f:
            f.write(FAKE_EDITOR)
        os.chmod(editor, os.stat(editor).st_mode | stat.S_IEXEC)
        self.env = {"HOME": self.home, "PATH": bin_dir + os.pathsep + os.environ["PATH"],
                    "SHELL": "/bin/bash", "TERM": "dumb"}
        # The main Claude login: a personal account.
        self.write(".claude/settings.json", {"theme": "dark"})
        self.write(".claude.json", {"oauthAccount": {"emailAddress": "me@example.com"},
                                    "hasCompletedOnboarding": True,
                                    "projects": {"/code": {"hasTrustDialogAccepted": True,
                                                           "lastCost": 1.5}}})
        self.write(".claude/.credentials.json", {"claudeAiOauth": {"accessToken": "t",
                                                                    "subscriptionType": "pro"}})
        self.write(".claude/projects/keep-me.txt", "shared history")
        os.makedirs(self.path("code/acme/app"))
        os.makedirs(self.path("code/other"))

    def tearDown(self):
        shutil.rmtree(self.home)

    # helpers ---------------------------------------------------------------

    def path(self, rel):
        return os.path.join(self.home, rel)

    def write(self, rel, content):
        p = self.path(rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(content if isinstance(content, str) else json.dumps(content))

    def read(self, rel):
        with open(self.path(rel)) as f:
            return f.read()

    def hat(self, *args, cwd=None, env=None, stdin=None, ok=True):
        r = subprocess.run([sys.executable, HAT] + list(args), cwd=cwd or self.home,
                           env=dict(self.env, **(env or {})), input=stdin,
                           capture_output=True, text=True)
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def sign_in(self, profile, email, org="Acme"):
        d = ".claude-profiles/" + profile
        self.write(d + "/.claude.json", {"oauthAccount": {"emailAddress": email,
                                                          "organizationName": org}})
        self.write(d + "/.credentials.json", {"claudeAiOauth": {"accessToken": "t",
                                                                 "subscriptionType": "team"}})

    def claude_calls(self):
        try:
            with open(self.path("claude-calls.log")) as f:
                return [json.loads(l) for l in f]
        except FileNotFoundError:
            return []

    # profiles and folders --------------------------------------------------

    def test_starts_with_the_main_login_as_personal(self):
        out = self.hat("status").stdout
        self.assertIn("personal", out)
        self.assertIn("me@example.com", out)
        self.assertIn("profile personal native", self.read(".config/hats/hats.conf"))

    def test_folder_rules_pick_the_profile_and_the_longest_rule_wins(self):
        self.hat("add", "work")
        self.hat("add", "client")
        self.hat("map", "work", self.path("code/acme"))
        self.hat("map", "client", self.path("code/acme/app"))
        self.assertEqual(self.hat("which", cwd=self.path("code/acme")).stdout.strip(), "work")
        self.assertEqual(self.hat("which", cwd=self.path("code/acme/app")).stdout.strip(), "client")
        self.assertEqual(self.hat("which", cwd=self.path("code/other")).stdout.strip(), "personal")
        self.hat("unmap", self.path("code/acme/app"))
        self.assertEqual(self.hat("which", cwd=self.path("code/acme/app")).stdout.strip(), "work")

    def test_a_pin_beats_the_folder(self):
        self.hat("add", "work")
        self.hat("map", "work", self.path("code/acme"))
        out = self.hat("which", cwd=self.path("code/acme"), env={"HAT_PIN": "personal"}).stdout
        self.assertEqual(out.strip(), "personal")

    def test_add_links_shared_items_and_copies_no_account(self):
        self.hat("add", "work", "me@acme.example")
        d = self.path(".claude-profiles/work")
        self.assertEqual(os.path.realpath(os.path.join(d, "projects")), os.path.realpath(self.path(".claude/projects")))
        self.assertEqual(os.path.realpath(os.path.join(d, "settings.json")),
                         os.path.realpath(self.path(".claude/settings.json")))
        seeded = json.loads(self.read(".claude-profiles/work/.claude.json"))
        self.assertNotIn("oauthAccount", seeded)
        self.assertEqual(seeded["projects"], {"/code": {"hasTrustDialogAccepted": True}})
        self.assertFalse(os.path.exists(os.path.join(d, ".credentials.json")))

    def test_wrong_account_is_flagged(self):
        self.hat("add", "work", "me@acme.example")
        self.sign_in("work", "someone@else.example")
        self.assertIn("wrong account", self.hat("status").stdout)

    def test_email_case_does_not_matter(self):
        self.hat("add", "work", "Me@Acme.Example")
        self.sign_in("work", "me@acme.example")
        self.assertNotIn("wrong account", self.hat("status").stdout)

    def test_profile_folders_may_contain_spaces(self):
        self.hat("status")  # creates the config
        with open(self.path(".config/hats/hats.conf"), "a") as f:
            f.write("profile spaced %s me@acme.example\n" % self.path("my profiles/spaced"))
        self.hat("--shell", "bash", "--eval", "use", "spaced")
        out = self.hat("--shell", "bash", "--eval", "use", "spaced").stdout
        self.assertIn("export CLAUDE_CONFIG_DIR='%s'" % self.path("my profiles/spaced"), out)

    def test_your_own_claude_config_dir_becomes_the_personal_profile(self):
        own = self.path("my-claude")
        os.makedirs(own)
        self.hat("status", env={"CLAUDE_CONFIG_DIR": own})
        conf = self.read(".config/hats/hats.conf")
        self.assertIn("base %s" % own, conf)
        self.assertIn("profile personal %s" % own, conf)
        self.hat("add", "work")
        self.assertEqual(os.path.realpath(self.path(".claude-profiles/work/projects")),
                         os.path.realpath(os.path.join(own, "projects")))

    def test_a_pin_to_a_removed_profile_says_how_to_recover(self):
        r = self.hat("claude", env={"HAT_PIN": "gone"}, ok=False)
        self.assertIn("hat auto", r.stderr)
        self.assertEqual(self.claude_calls(), [])

    def test_claudes_exit_code_comes_back(self):
        with open(self.path("bin/claude"), "a") as f:
            f.write("sys.exit(7)\n")
        self.assertEqual(self.hat("claude", ok=False).returncode, 7)

    def test_bad_input_is_refused_with_a_message(self):
        for args in (["use", "nope"], ["add", "bad name"], ["map", "personal", "/no/such/dir"], ["frobnicate"]):
            r = self.hat(*args, ok=False)
            self.assertEqual(r.returncode, 2, args)
            self.assertTrue(r.stderr.startswith("hat: "), r.stderr)

    # launching claude ------------------------------------------------------

    def test_claude_runs_on_the_folders_profile(self):
        self.hat("add", "work")
        self.sign_in("work", "me@acme.example")
        self.hat("map", "work", self.path("code/acme"))
        self.hat("claude", "--version", cwd=self.path("code/acme"))
        self.hat("claude", "--version", cwd=self.path("code/other"))
        calls = self.claude_calls()
        self.assertEqual(calls[0], {"dir": self.path(".claude-profiles/work"), "args": ["--version"]})
        self.assertEqual(calls[1], {"dir": "", "args": ["--version"]})

    def test_inside_claude_code_the_account_is_left_alone(self):
        self.hat("add", "work")
        self.hat("map", "work", self.path("code/acme"))
        self.hat("claude", "-p", "hi", cwd=self.path("code/acme"),
                 env={"CLAUDECODE": "1", "CLAUDE_CONFIG_DIR": "/parent/session"})
        self.assertEqual(self.claude_calls()[0]["dir"], "/parent/session")

    def test_switch_commands_print_shell_code(self):
        self.hat("add", "work")
        bash = self.hat("--shell", "bash", "--eval", "use", "work").stdout
        self.assertIn("export CLAUDE_CONFIG_DIR='%s'" % self.path(".claude-profiles/work"), bash)
        self.assertIn("export HAT_PIN='work'", bash)
        pwsh = self.hat("--shell", "pwsh", "--eval", "auto").stdout
        self.assertIn("Remove-Item Env:HAT_PIN", pwsh)
        r = self.hat("use", "work", ok=False)  # without the shell hook there is nothing to change
        self.assertEqual(r.returncode, 2)

    def test_prompt_markers_suit_each_shell(self):
        bash = self.hat("--shell", "bash", "prompt").stdout
        zsh = self.hat("--shell", "zsh", "prompt").stdout
        pwsh = self.hat("--shell", "pwsh", "prompt").stdout
        self.assertIn("\x01\x1b[1;38;5;114m\x02personal", bash)
        self.assertIn("%{\x1b[1;38;5;114m%}personal", zsh)
        self.assertTrue(pwsh.startswith("\x1b[1;38;5;114mpersonal"))
        self.assertTrue(pwsh.endswith("\x1fpersonal — ~"))

    def test_status_line_shows_the_account_and_records_usage(self):
        self.hat("add", "work")
        self.sign_in("work", "me@acme.example")
        data = json.dumps({"model": {"display_name": "Opus"},
                           "rate_limits": {"five_hour": {"used_percentage": 12, "resets_at": 9999999999}}})
        out = self.hat("statusline", stdin=data,
                       env={"CLAUDE_CONFIG_DIR": self.path(".claude-profiles/work")}).stdout
        self.assertIn("work", out)
        self.assertIn("Acme", out)
        self.assertIn("12%", out)
        self.assertTrue(self.read(".config/hats/usage/work").startswith("12|"))

    # sharing never breaks the user's own files ---------------------------

    def test_a_saved_settings_file_is_merged_without_breaking_a_dotfiles_link(self):
        # ~/.claude/settings.json is itself a link into a dotfiles folder.
        self.write("dotfiles/claude-settings.json", '{"theme": "dark"}')
        os.remove(self.path(".claude/settings.json"))
        os.symlink(self.path("dotfiles/claude-settings.json"), self.path(".claude/settings.json"))
        self.hat("add", "work")
        # Claude saved settings in the profile by replacing the link with a real file.
        prof = self.path(".claude-profiles/work/settings.json")
        os.remove(prof)
        self.write(".claude-profiles/work/settings.json", '{"theme": "light"}')
        os.utime(prof, (2e9, 2e9))
        self.hat("run", "work")
        self.assertTrue(os.path.islink(self.path(".claude/settings.json")))
        self.assertEqual(self.read("dotfiles/claude-settings.json"), '{"theme": "light"}')
        self.assertTrue(os.path.islink(prof))

    def test_remove_signs_out_and_keeps_shared_data(self):
        self.hat("add", "work")
        self.sign_in("work", "me@acme.example")
        self.hat("map", "work", self.path("code/acme"))
        self.hat("remove", "work", "--yes")
        self.assertFalse(os.path.exists(self.path(".claude-profiles/work")))
        self.assertEqual(self.read(".claude/projects/keep-me.txt"), "shared history")
        self.assertTrue(os.path.exists(self.path(".claude/settings.json")))
        conf = self.read(".config/hats/hats.conf")
        self.assertNotIn("work", conf)
        self.assertIn(["auth", "logout"], [c["args"] for c in self.claude_calls()])

    def test_remove_refuses_the_main_login_and_the_default(self):
        self.hat("add", "work")
        self.assertIn("main Claude login", self.hat("remove", "personal", "--yes", ok=False).stderr)
        self.hat("default", "work")
        self.assertIn("default profile", self.hat("remove", "work", "--yes", ok=False).stderr)

    def test_remove_asks_first(self):
        self.hat("add", "work")
        r = self.hat("remove", "work", ok=False)  # no terminal and no --yes
        self.assertEqual(r.returncode, 2)
        self.assertTrue(os.path.exists(self.path(".claude-profiles/work")))

    # installer -------------------------------------------------------------

    def install(self, *args, stdin=None):
        r = subprocess.run([sys.executable, INSTALL] + list(args), env=self.env, input=stdin,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_install_and_uninstall_leave_startup_files_byte_for_byte(self):
        original = b"# my bashrc\r\nexport X=1\r\n\xff\xfe odd bytes\r\nalias ll='ls -l'"
        with open(self.path(".bashrc"), "wb") as f:
            f.write(original)
        self.install("--shell", "bash")
        self.install("--shell", "bash")  # running twice keeps one line
        with open(self.path(".bashrc"), "rb") as f:
            installed = f.read()
        self.assertEqual(installed.count(b"# hats: Claude Code accounts"), 1)
        self.assertTrue(installed.startswith(original))
        self.install("--uninstall")
        with open(self.path(".bashrc"), "rb") as f:
            self.assertEqual(f.read(), original + b"\r\n")

    def test_install_keeps_an_existing_status_line(self):
        self.write(".claude/settings.json", {"statusLine": {"type": "command", "command": "my-line"}})
        out = self.install("--shell", "bash")
        self.assertIn("kept your own", out)
        self.assertEqual(json.loads(self.read(".claude/settings.json"))["statusLine"]["command"], "my-line")
        self.install("--uninstall")
        self.assertEqual(json.loads(self.read(".claude/settings.json"))["statusLine"]["command"], "my-line")

    def test_install_leaves_unreadable_settings_alone(self):
        self.write(".claude/settings.json", "{ not json")
        out = self.install("--shell", "bash")
        self.assertIn("not valid JSON", out)
        self.assertEqual(self.read(".claude/settings.json"), "{ not json")

    def test_status_line_is_added_and_removed(self):
        self.install("--shell", "bash")
        self.assertIn("statusline", json.loads(self.read(".claude/settings.json"))["statusLine"]["command"])
        self.install("--uninstall")
        self.assertEqual(json.loads(self.read(".claude/settings.json")), {"theme": "dark"})

    def test_purge_deletes_profiles_but_never_follows_links_into_claude(self):
        self.install("--shell", "bash")
        self.hat("add", "work")
        self.sign_in("work", "me@acme.example")
        self.install("--uninstall", "--purge", stdin="y\n")
        self.assertFalse(os.path.exists(self.path(".claude-profiles")))
        self.assertFalse(os.path.exists(self.path(".config/hats")))
        self.assertEqual(self.read(".claude/projects/keep-me.txt"), "shared history")
        self.assertTrue(os.path.exists(self.path(".claude/.credentials.json")))

    def test_settings_keep_their_format_through_install_and_uninstall(self):
        original = '{\n    "theme": "dark",\n    "note": "café"\n}\n'
        self.write(".claude/settings.json", original)
        self.install("--shell", "bash")
        self.assertIn('\n    "statusLine"', self.read(".claude/settings.json"))
        self.install("--uninstall")
        self.assertEqual(self.read(".claude/settings.json"), original)

    def test_uninstall_keeps_a_status_line_that_only_looks_like_ours(self):
        cmd = "~/bin/my-hat-statusline"
        self.write(".claude/settings.json", {"statusLine": {"type": "command", "command": cmd}})
        self.install("--uninstall")
        self.assertEqual(json.loads(self.read(".claude/settings.json"))["statusLine"]["command"], cmd)

    def test_install_works_when_the_home_folder_has_a_quote_in_its_name(self):
        odd = os.path.join(self.home, "O'Brien")
        os.makedirs(odd)
        self.env["HOME"] = odd
        with open(os.path.join(odd, ".bashrc"), "w") as f:
            f.write("# rc\n")
        self.install("--shell", "bash")
        r = subprocess.run(["bash", "-n", os.path.join(odd, ".bashrc")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run(["bash", "-c", "source ~/.bashrc; type -t hat"], env=self.env,
                           capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "function", r.stderr)

    def test_utf16_powershell_profiles_stay_utf16(self):
        sys.path.insert(0, REPO)
        import install
        p = self.path("profile.ps1")
        with open(p, "w", encoding="utf-16") as f:
            f.write("Set-Alias ll Get-ChildItem\r\n")
        install.add_line(p, "$x = 1  " + install.MARKER)
        with open(p, encoding="utf-16", newline="") as f:
            self.assertEqual(f.read(), "Set-Alias ll Get-ChildItem\r\n\r\n$x = 1  " + install.MARKER + "\r\n")
        install.strip_marker(p)
        with open(p, encoding="utf-16", newline="") as f:
            self.assertEqual(f.read(), "Set-Alias ll Get-ChildItem\r\n")

    def test_bash_hook_only_drops_the_title_at_the_start_of_the_prompt(self):
        self.install("--shell", "bash")
        ps1 = r'\[\e]0;\u@\h: \w\a\]\u@\h:\w\[\e]133;A\a\]\$ '
        script = "PS1='%s'; source ~/.config/hats/hat.bash; printf '%%s' \"$PS1\"" % ps1
        r = subprocess.run(["bash", "-ic", script], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.stdout, r'${HAT__SEG}\u@\h:\w\[\e]133;A\a\]\$ ')

    def test_bash_hook_falls_back_to_plain_claude_when_hat_is_gone(self):
        self.install("--shell", "bash")
        os.remove(self.path(".config/hats/hat.py"))
        r = subprocess.run(["bash", "-c", "source ~/.config/hats/hat.bash; claude --version"],
                           env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.claude_calls(), [{"dir": "", "args": ["--version"]}])

    # added features ---------------------------------------------------------

    def test_a_separate_profile_keeps_its_own_history(self):
        self.hat("add", "client", "--separate")
        d = self.path(".claude-profiles/client")
        self.assertFalse(os.path.islink(os.path.join(d, "projects")))
        self.assertFalse(os.path.exists(os.path.join(d, "projects/keep-me.txt")))
        self.assertTrue(os.path.islink(os.path.join(d, "settings.json")))  # settings still shared
        self.assertIn("separate client", self.read(".config/hats/hats.conf"))
        self.assertIn("separate", self.hat("status").stdout)

    def test_marking_a_profile_separate_later_unlinks_only(self):
        self.hat("add", "client")
        with open(self.path(".config/hats/hats.conf"), "a") as f:
            f.write("separate client\n")
        self.hat("run", "client")
        d = self.path(".claude-profiles/client")
        self.assertFalse(os.path.islink(os.path.join(d, "projects")))
        self.assertEqual(self.read(".claude/projects/keep-me.txt"), "shared history")

    def test_claude_refuses_to_start_on_the_wrong_account(self):
        self.hat("add", "work", "me@acme.example")
        self.sign_in("work", "someone@else.example")
        self.hat("map", "work", self.path("code/acme"))
        r = self.hat("claude", cwd=self.path("code/acme"), ok=False)
        self.assertEqual(r.returncode, 2)
        self.assertIn("should be me@acme.example", r.stderr)
        self.assertEqual(self.claude_calls(), [])

    def test_a_login_with_the_wrong_account_is_signed_out_again(self):
        self.hat("add", "work", "me@acme.example")
        r = self.hat("login", "work", env={"FAKE_EMAIL": "someone@else.example"}, ok=False)
        self.assertIn("signed it out again", r.stdout)
        self.assertFalse(os.path.exists(self.path(".claude-profiles/work/.credentials.json")))
        self.hat("login", "work", env={"FAKE_EMAIL": "me@acme.example"})
        self.assertIn("me@acme.example", self.hat("status").stdout)

    def test_claude_warns_near_a_usage_limit(self):
        self.write(".config/hats/usage/personal", "93|9999999999|40|9999999999\n")
        r = self.hat("claude")
        self.assertIn("'personal' has 7% left of its 5-hour limit", r.stderr)
        self.assertNotIn("weekly", r.stderr)

    # automatic switching ----------------------------------------------------

    def switching(self, *order, level="10"):
        self.hat("add", "work")
        self.sign_in("work", "me@acme.example")
        self.hat("add", "client")
        self.sign_in("client", "me@client-a.example")
        self.hat("settings", "switch", "on")
        self.hat("settings", "level", level)
        self.hat("settings", "order", *order)

    def pty_hat(self, args, keys, env=None, timeout=10):
        """Run hat.py in a pseudo-terminal, type `keys` (a list of (wait seconds, bytes)),
        and return everything it showed."""
        import pty
        import select
        import time
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(self.home)
            os.execve(sys.executable, [sys.executable, HAT] + args, dict(self.env, TERM="xterm", **(env or {})))
        out, end = b"", time.time() + timeout
        keys = list(keys)
        next_at = time.time() + (keys[0][0] if keys else 0)
        while time.time() < end:
            if keys and time.time() >= next_at:
                os.write(fd, keys.pop(0)[1])
                next_at = time.time() + (keys[0][0] if keys else 0)
            if select.select([fd], [], [], 0.05)[0]:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                out += chunk
        _, status = os.waitpid(pid, 0)
        os.close(fd)
        self.assertEqual(os.WEXITSTATUS(status), 0, out.decode("utf-8", "replace"))
        return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", out.decode("utf-8", "replace"))

    def test_settings_are_saved_and_shown(self):
        out = re.sub(r"\x1b\[[0-9;]*m", "", self.hat("settings").stdout)
        self.assertIn("Move to another account when one runs low     [ off ]", out)
        self.assertIn("Now: nothing moves.", out)
        self.switching("personal", "work")
        conf = self.read(".config/hats/hats.conf")
        self.assertIn("switch on\n", conf)
        self.assertIn("switch_left 10\n", conf)
        self.assertIn("order personal work\n", conf)
        out = re.sub(r"\x1b\[[0-9;]*m", "", self.hat("settings").stdout)
        self.assertRegex(out, r"Take turns, top first\s+left now\n\s+1  personal\s+no usage yet\n\s+2  work\s+no usage yet")
        self.assertRegex(out, r"Never switch to or from\n\s+client\n")
        self.assertIn("Now: claude starts on personal. When it has less than 10%", out)
        data = json.loads(self.hat("status", "--json").stdout)
        self.assertEqual(data["switching"], {"on": True, "left_below": 10, "order": ["personal", "work"]})
        r = self.hat("settings", "level", "60", ok=False)
        self.assertEqual(r.returncode, 2)
        self.assertIn("from 5 to 50", r.stderr)
        self.assertIn("unknown profile 'nobody'", self.hat("settings", "order", "nobody", ok=False).stderr)
        self.hat("settings", "switch", "off")
        self.assertIn("Automatic switching: off", self.hat("status").stdout)
        self.assertIn("order personal work", self.read(".config/hats/hats.conf"), "the order is kept while off")

    def test_claude_starts_on_the_next_account_in_the_order_when_one_is_low(self):
        self.switching("personal", "work", "client")
        self.write(".config/hats/usage/personal", "93|9999999999|40|9999999999\n")
        self.write(".config/hats/usage/work", "20|9999999999|95|9999999999\n")   # week is low too
        r = self.hat("claude", "--model", "x")
        self.assertIn("'personal' has 7% left of its 5-hour limit", r.stderr)
        self.assertIn("starting on 'client'", r.stderr)
        self.assertEqual(self.claude_calls()[-1], {"dir": self.path(".claude-profiles/client"), "args": ["--model", "x"]})
        self.hat("claude", "auth", "login")
        self.assertEqual(self.claude_calls()[-1], {"dir": "", "args": ["auth", "login"]},
                         "signing in stays on the account in the prompt")
        self.hat("claude", "-p", "hi")
        self.assertEqual(self.claude_calls()[-1]["dir"], self.path(".claude-profiles/client"), "-p uses the limits")

    def test_claude_stays_put_when_switching_is_off_or_the_account_is_not_in_the_order(self):
        self.switching("work", "client")
        self.write(".config/hats/usage/personal", "99|9999999999|40|9999999999\n")
        r = self.hat("claude")
        self.assertNotIn("starting on", r.stderr, "personal is not in the order")
        self.assertEqual(self.claude_calls()[-1]["dir"], "")
        self.hat("settings", "order", "personal", "work")
        self.hat("settings", "switch", "off")
        self.hat("claude")
        self.assertEqual(self.claude_calls()[-1]["dir"], "", "switching is off")
        self.hat("settings", "switch", "on")
        self.write(".config/hats/usage/work", "99|9999999999|40|9999999999\n")
        r = self.hat("claude")
        self.assertIn("and so has every other account in your order", r.stderr)
        self.assertEqual(self.claude_calls()[-1]["dir"], "")

    def test_a_chat_carries_on_on_the_next_account_after_asking(self):
        self.switching("personal", "work")
        status = json.dumps({"session_id": "chat-123", "rate_limits": {
            "five_hour": {"used_percentage": 96, "resets_at": 9999999999},
            "seven_day": {"used_percentage": 30, "resets_at": 9999999999}}})
        out = self.pty_hat(["claude"], [(1.5, b"\r")], env={"FAKE_STATUS": status, "FAKE_HAT": HAT})
        self.assertIn("'personal' has 4% left of its 5-hour limit", out)
        self.assertIn("Continue this chat on 'work'? [Y/n]", out)
        calls = self.claude_calls()
        self.assertEqual(calls[0], {"dir": "", "args": []})
        self.assertEqual(calls[1], {"dir": self.path(".claude-profiles/work"), "args": ["--resume", "chat-123"]})
        self.assertEqual(os.listdir(self.path(".config/hats/runs")), [], "the note of the chat is removed")

    def test_answering_no_keeps_the_chat_where_it_is(self):
        self.switching("personal", "work")
        status = json.dumps({"session_id": "chat-123", "rate_limits": {"five_hour": {"used_percentage": 96}}})
        self.pty_hat(["claude"], [(1.5, b"n\r")], env={"FAKE_STATUS": status, "FAKE_HAT": HAT})
        self.assertEqual(len(self.claude_calls()), 1)

    def test_status_line_offers_the_handover_only_in_a_watched_run(self):
        self.switching("personal", "work")
        data = json.dumps({"session_id": "c1", "rate_limits": {"five_hour": {"used_percentage": 95}}})
        run = "0123456789abcdef0123456789abcdef"
        out = self.hat("statusline", stdin=data, env={"HAT_RUN": run}).stdout
        self.assertIn("/exit → continue on work", out)
        self.assertEqual(self.read(".config/hats/runs/" + run).strip(), "c1")
        self.assertNotIn("/exit", self.hat("statusline", stdin=data).stdout)
        bad = self.hat("statusline", stdin=data, env={"HAT_RUN": "../../evil"}).stdout
        self.assertNotIn("/exit", bad)
        self.assertFalse(os.path.exists(self.path(".config/evil")))

    def test_settings_screen_by_keys(self):
        self.hat("add", "work")
        down, up, left, space, enter = b"\x1b[B", b"\x1b[A", b"\x1b[D", b" ", b"\r"
        keys = [space,            # switching on
                down, left,       # level: 10% -> 5% left
                down, enter, up, enter,         # pick up personal, into Take turns, drop
                down, enter, up, enter,         # the same for work: it lands under personal
                enter, up, enter,               # pick work up again and move it above personal
                b"q"]
        out = self.pty_hat(["settings"], [(0.8, keys[0])] + [(0.25, k) for k in keys[1:]])
        self.assertIn("Hats · Settings", out)
        self.assertIn("enter: pick up an account, ↑↓ move, enter drop", out)
        self.assertIn("↑↓ move it · enter drop · esc put it back", out)
        conf = self.read(".config/hats/hats.conf")
        self.assertIn("switch on\n", conf)
        self.assertIn("switch_left 5\n", conf)
        self.assertIn("order work personal\n", conf)

    def test_esc_puts_a_picked_up_account_back(self):
        self.hat("add", "work")
        self.hat("settings", "switch", "on")
        self.hat("settings", "order", "personal")
        down, up, enter = b"\x1b[B", b"\x1b[A", b"\r"
        keys = [down, down, down, enter, up, b"\x1b", b"q"]   # pick up work, move it, then esc
        self.pty_hat(["settings"], [(0.8, keys[0])] + [(0.25, k) for k in keys[1:]])
        self.assertIn("order personal\n", self.read(".config/hats/hats.conf"))

    def test_status_shows_what_is_left_and_when_it_resets(self):
        self.write(".config/hats/usage/personal", "12|9999999999|85|9999999999\n")
        self.hat("add", "work")
        self.sign_in("work", "me@acme.example")
        out = re.sub(r"\x1b\[[0-9;]*m", "", self.hat("status").stdout)
        self.assertRegex(out, r"5h 88% left \(resets \d\d:\d\d\) · week 15% left \(resets \w{3} \d\d:\d\d\)")
        self.assertIn("no usage yet", out)
        data = json.loads(self.hat("status", "--json").stdout)
        self.assertEqual((data["profiles"][0]["left_5h"], data["profiles"][0]["left_week"]), (88, 15))

    def test_status_json(self):
        self.hat("add", "work", "me@acme.example")
        self.hat("map", "work", self.path("code/acme"))
        data = json.loads(self.hat("status", "--json", cwd=self.path("code/acme")).stdout)
        self.assertEqual(data["active"], "work")
        self.assertEqual([p["name"] for p in data["profiles"]], ["personal", "work"])
        self.assertEqual(data["profiles"][0]["state"], "ok")
        self.assertEqual(data["rules"], [{"profile": "work", "folder": self.path("code/acme")}])

    def test_export_and_import_move_profiles_and_rules_but_no_logins(self):
        self.hat("add", "work", "me@acme.example")
        self.hat("add", "client", "--separate")
        self.sign_in("work", "me@acme.example")
        self.hat("map", "work", self.path("code/acme"))
        self.hat("export", self.path("setup.json"))
        exported = self.read("setup.json")
        self.assertNotIn("accessToken", exported)
        # A second computer: a fresh config.
        shutil.rmtree(self.path(".config/hats"))
        shutil.rmtree(self.path(".claude-profiles"))
        out = self.hat("import", self.path("setup.json")).stdout
        self.assertIn("imported 2 profiles and 1 folder rule", out)
        conf = self.read(".config/hats/hats.conf")
        self.assertIn("profile work ~/.claude-profiles/work me@acme.example", conf)
        self.assertIn("separate client", conf)
        self.assertEqual(self.hat("which", cwd=self.path("code/acme")).stdout.strip(), "work")
        self.assertIn("not signed in", self.hat("status").stdout)

    def test_doctor_finds_and_fixes_a_broken_link(self):
        self.hat("add", "work")
        self.sign_in("work", "me@acme.example")
        os.remove(self.path(".claude-profiles/work/projects"))
        r = self.hat("doctor", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not linked as it should be: projects", r.stdout)
        self.hat("doctor", "--fix", env={"HAT_HOOK": "bash"})
        self.assertTrue(os.path.islink(self.path(".claude-profiles/work/projects")))

    def test_context_tells_claude_the_account(self):
        self.hat("add", "work")
        self.sign_in("work", "me@acme.example", org="Acme")
        out = self.hat("context", env={"CLAUDE_CONFIG_DIR": self.path(".claude-profiles/work")}).stdout
        self.assertIn("profile 'work' (me@acme.example, Acme)", out)
        self.assertFalse(out.startswith("{"))  # Claude Code reads plain text as context

    def test_install_adds_the_account_hook_next_to_existing_hooks(self):
        mine = {"matcher": "startup", "hooks": [{"type": "command", "command": "echo hi"}]}
        self.write(".claude/settings.json", {"hooks": {"SessionStart": [mine]}})
        self.install("--shell", "bash")
        self.install("--shell", "bash")  # twice: still one hat hook
        hooks = json.loads(self.read(".claude/settings.json"))["hooks"]["SessionStart"]
        self.assertEqual(len(hooks), 2)
        self.assertEqual(hooks[0], mine)
        self.assertTrue(hooks[1]["hooks"][0]["command"].endswith('hat.py" context'))
        self.install("--uninstall")
        self.assertEqual(json.loads(self.read(".claude/settings.json")), {"hooks": {"SessionStart": [mine]}})

    def test_code_opens_an_editor_window_of_its_own_on_the_profile(self):
        self.hat("add", "work")
        self.hat("code", "work", self.path("code/acme"))
        with open(self.path("editor-calls.log")) as f:
            call = json.loads(f.readline())
        self.assertEqual(call["dir"], self.path(".claude-profiles/work"))
        self.assertIn("--user-data-dir", call["args"])
        self.assertEqual(call["args"][-1], self.path("code/acme"))

    def test_update_explains_when_it_cannot_tell_the_repository(self):
        r = self.hat("update", ok=False)
        self.assertIn("cannot tell which repository", r.stderr)

    def test_install_records_where_it_came_from(self):
        self.install("--shell", "bash")
        meta = json.loads(self.read(".config/hats/install.json"))
        self.assertEqual(meta["repo"], REPO)
        self.assertEqual(meta["shells"], ["bash"])


if __name__ == "__main__":
    unittest.main()
