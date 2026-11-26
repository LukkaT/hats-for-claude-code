# Automatic switching

When an account runs low on its Claude usage limits, Hats can move your work to
another account, **only between the accounts you choose, in the order you choose,
and never without telling you.** It is off until you turn it on.

![hat settings: turn switching on, choose when an account is low, choose which accounts take turns; then a chat continues on the next account](settings.gif)

- [Step by step](#step-by-step), one picture per step
- [In one minute](#in-one-minute)
- [Setting it up](#setting-it-up)
- [The screen, line by line](#the-screen-line-by-line)
- [What "low" means, exactly](#what-low-means-exactly)
- [Which account takes over](#which-account-takes-over)
- [When it happens](#when-it-happens)
- [When it never happens](#when-it-never-happens)
- [What you see while it works](#what-you-see-while-it-works)
- [Work, client and personal accounts](#work-client-and-personal-accounts)
- [Without the screen](#without-the-screen)
- [Questions](#questions)

## Step by step

Open one step at a time. Each picture shows the key you press (bottom right) and, in blue, what changed.

<details open>
<summary><b>Step 1 of 9: Open the settings</b></summary>

![Step 1: Open the settings](settings/step-1.png)

**You press:** Type `hat settings` and press **Enter**.

**What happens:** The settings open. The first line says **[ off ]**: while it's off, nothing ever moves. Every folder keeps its own account, as before.

</details>

<details>
<summary><b>Step 2 of 9: Turn it on</b></summary>

![Step 2: Turn it on](settings/step-2.png)

**You press:** **Space** on the first line.

**What happens:** It says **[ on ]**. Nothing moves yet, though: you still need to choose which accounts take turns (step 4).

</details>

<details>
<summary><b>Step 3 of 9: Choose when an account counts as low</b></summary>

![Step 3: Choose when an account counts as low](settings/step-3.png)

**You press:** **↓** to the second line, then **←** or **→**.

**What happens:** The number changes in steps of 5 (from 5% to 50%). With 15%, an account is **low** as soon as **either** of its limits, the 5-hour one or the weekly one, has less than 15% left.

</details>

<details>
<summary><b>Step 4 of 9: Choose who takes turns</b></summary>

![Step 4: Choose who takes turns](settings/step-4.png)

**You press:** **↓** to an account under *Never switch to or from*. **Enter** picks it up (⇅), **↑** carries it into *Take turns*, **Enter** puts it down.

**What happens:** The account now takes turns. The first one in the list is used first. Do the same for every account that may take over; the order is the order you put them in, and you can carry an account up or down again at any time.

</details>

<details>
<summary><b>Step 5 of 9: Leave out accounts that must not switch</b></summary>

![Step 5: Leave out accounts that must not switch](settings/step-5.png)

**You press:** Nothing: just don't move them.

**What happens:** Accounts left under **Never switch to or from** (here `client-a`) are never used for someone else's work, and work started on them never moves away. Use this for accounts of employers or clients who want their work on their own access.

</details>

<details>
<summary><b>Step 6 of 9: Read the Now line</b></summary>

![Step 6: Read the Now line](settings/step-6.png)

**You press:** Nothing: it updates by itself.

**What happens:** The **Now:** line says in plain words what `claude` will do in this terminal with these settings. Here: it starts on personal, and moves on to work when personal has less than 15% left. Press **Esc** to close; every change is already saved.

</details>

<details>
<summary><b>Step 7 of 9: Later, in a chat: the account gets low</b></summary>

![Step 7: Later, in a chat: the account gets low](settings/step-7.png)

**You press:** Nothing: keep working.

**What happens:** Claude's status line shows `low: moves to work after this task`. Claude keeps working on the current task as usual. Nothing is cut off.

</details>

<details>
<summary><b>Step 8 of 9: The task finishes: the chat moves by itself</b></summary>

![Step 8: The task finishes: the chat moves by itself](settings/step-8.png)

**You press:** Nothing. No `/exit`, no question.

**What happens:** As soon as Claude has finished the task, Hats closes Claude and says `hat: 'personal' has 8% left of its 5-hour limit → this chat continues on 'work' …`. If the limit had run out **in the middle** of the task instead, the task would continue on work by itself.

</details>

<details>
<summary><b>Step 9 of 9: The same chat, now on work</b></summary>

![Step 9: The same chat, now on work](settings/step-9.png)

**You press:** Type your next message as usual.

**What happens:** Claude is open again with **the same chat**: everything said so far is still there. The status line now shows **work**. If work gets low later, the same happens again with the next account.

</details>

## In one minute

1. You put accounts in a list called **Take turns**, top first. Every other account
   stays under **Never switch to or from**, and Hats never moves work to or from it.
2. You choose when an account counts as **low**, for example *less than 10% left* of
   its 5-hour or weekly limit.
3. When you type `claude` and the account for this folder is low, Claude starts on
   the next account in Take turns instead, and Hats says so.
4. When an account gets low **during** a chat, the same chat moves to the next account
   by itself **as soon as the current task finishes**. If the limit runs out in the
   middle of a task, the task continues on the next account.

Nothing is cut off in the middle of a task. A chat moves when a task has finished, or
when the account really can't go on.

## Setting it up

Type `hat settings`. With your keyboard:

1. **Space** turns *Move to another account when one runs low* on.
2. **↓** to *Runs low = less than … left*, then **← →** to choose the level
   (5% to 50%, in steps of 5; 10% to start).
3. **↓** to an account under *Never switch to or from*. **Enter** picks it up (a ⇅
   appears), **↑** carries it into *Take turns*, **Enter** puts it down.
4. Do the same for the second account. The order matters: the higher one is used first.
5. Read the **Now:** line. It says in plain words what `claude` will do here.
6. **Esc** closes the screen. Every change is saved at once; there is no "save" step.

You need at least two accounts under Take turns. With one, there is nowhere to move to.

## The screen, line by line

```
 Hats · Settings                                   esc close

 ❯ Move to another account when one runs low     [ on ]
   Runs low = less than  10%  left of its 5-hour or weekly limit

   Take turns, top first                      left now
     1  personal                              58%
     2  work                                  97%

   Never switch to or from
        client-a

   Now: claude starts on personal. When it has less than 10%
   left, it moves on to work.

 space on/off · ←→ change · enter: pick up an account, ↑↓ move, enter drop
```

| Line | What it means |
| --- | --- |
| **Move to another account when one runs low `[ on ]`** | The main switch. `[ off ]`: nothing ever moves. Every folder keeps its own account, exactly as without this feature. Your list is kept, but greyed out and not used. |
| **Runs low = less than 10% left** | When an account counts as low. It looks at both limits: the 5-hour one and the weekly one. If **either** has less than this left, the account is low. |
| **Take turns, top first** | The accounts allowed to take over from each other. Number 1 is used first. |
| **left now** | How much is left of the account's **tighter** limit, the smaller of its 5-hour and weekly numbers. It shows *no usage yet* when Hats hasn't seen that account used yet ([why](#what-low-means-exactly)), and *not signed in, skipped* when it can't be used. |
| **Never switch to or from** | Accounts that are left out completely. Work never moves to them, and work started on them never moves away. |
| **Now:** | What `claude` will do in **this** terminal and folder, with the settings as they are on screen. It changes as you change things. |

**Keys**

| Key | Where | What it does |
| --- | --- | --- |
| ↑ ↓ | anywhere | Move the cursor (❯). |
| Space | the first line | Turn switching on or off. |
| ← → | the level | Less or more left before an account counts as low. |
| Enter | an account | Pick it up (⇅). Then ↑ ↓ carry it, even from one list into the other, and Enter puts it down. Esc puts it back where it was. |
| Space | an account | Shortcut: move it straight to the other list (to the bottom of Take turns, or out of it). |
| Esc or q | anywhere | Close. Changes are already saved. |

## What "low" means, exactly

- **Two limits.** Claude has a 5-hour limit and a weekly limit. An account is low when
  **either** has *less than* your level left. With 10%: 9% left is low, 10% is not.
- **Where the numbers come from.** Claude Code reports an account's limits while
  you use it, and Hats's status line writes them down. So Hats knows an account's
  numbers **from the last time Claude Code ran on it, on this computer.**
  - An account you haven't used here yet shows *no usage yet*, and counts as **having
    room**.
  - Use on claude.ai, the desktop app or another computer isn't seen until Claude
    Code runs on that account here again. An account can be lower than Hats thinks.
  - When a limit's reset time has passed, Hats counts it as full again, even before
    a new session reports the fresh number.
- `hat status` shows the same numbers, as *% left* and *when it resets*.

## Which account takes over

**The first account from the top of Take turns that isn't the one in use, is signed
in, and is not low.**

Example with Take turns: 1 `personal`, 2 `work`, 3 `client-b`

| In use | Situation | Takes over |
| --- | --- | --- |
| personal | personal is low; work has room | **work** |
| personal | personal and work are low | **client-b** |
| work | work is low; personal has room again | **personal** (it is higher in the list) |
| personal | work isn't signed in; client-b has room | **client-b** (work is skipped) |
| personal | everyone is low | **nobody**: Claude stays on personal, and Hats tells you |
| client-a | client-a is under *Never switch* | **nobody**: client-a never switches |

## When it happens

### When you start Claude

If the account for this folder (or the one you picked with `hat` / F2) is under Take
turns and low, Claude starts on the account that takes over:

```
personal you@laptop:~/code$ claude
hat: 'personal' has 6% left of its 5-hour limit (resets Thu 18:00) → starting on 'work' (automatic switching: hat settings)
```

This also applies to `claude -p "…"`, which uses the limits too. It does **not**
apply to commands that manage Claude itself (`claude auth …`, `claude mcp …`,
`claude config …`, `claude --version`), so `claude auth login` always signs in the
account shown in your prompt.

### During a chat

Claude Code can't change account while it runs, so Hats moves the chat **between two
runs** of Claude: it closes Claude and opens the same chat again on the next account.
It never does that in the middle of a task.

**When a task finishes and the account is low**, it moves by itself:

1. While you work, Claude's status line shows the numbers. Once the account is low,
   it adds `low: moves to work after this task`.
2. Claude finishes what it is doing (the reply, the edits, the tests), as usual.
3. Right then, Hats closes Claude and says:

   ```
   hat: 'personal' has 8% left of its 5-hour limit → this chat continues on 'work' …
   ```

4. Claude opens again with **the same chat** (`claude --resume`). Everything said so
   far is there, and the status line now shows **work**. You type your next message
   as usual.

**When the limit runs out in the middle of a task**, for example during a long task
with little left, or when the weekly limit runs out:

1. Claude can't send its next request, and stops with a usage-limit message. Nothing
   is half-done: a command that was running has finished, and each file edit is
   either complete or not made.
2. Hats reopens the same chat on the next account and sends, for you:
   `Continue where you stopped: the previous account reached its usage limit.`
3. Claude reads the chat so far and carries on with the task.

```
hat: 'personal' reached its usage limit → continuing this task on 'work' …
```

**Good to know**

- **Same chat, new account.** A chat can move because all accounts share their history
  (the `projects/` folder, see [How it works](how-it-works.md#what-is-shared)). The
  first message on the new account reads the whole chat once, so it uses a little
  more of that account than usual.
- **`--separate` accounts** keep their history to themselves, so a chat can't move to
  or from them. They can still take over when Claude **starts**.
- **Options you started Claude with** (such as `--model`) aren't repeated. The
  continued chat starts with Claude's defaults.
- **Background tasks.** If Claude has something running in the background (for example
  a dev server it started), Hats doesn't close it after that task. It waits for a
  later task that ends with nothing running.
- **Typing quickly.** The move happens about a second after the task finishes. Text
  you had started typing in that second isn't carried over.
- **Over and over.** If work gets low later, the same happens again from work to the
  next account.
- **If the hooks are missing** (for example, an older install, or your own
  `settings.json` that Hats left alone), nothing moves by itself. Then, after you
  `/exit`, Hats asks `Continue this chat on 'work'? [Y/n]` instead.

**Watched chats.** For a chat on an account under Take turns, Hats stays running in
the background instead of handing over to Claude completely, so it can move the chat.
Ctrl-C still goes to Claude. Chats on other accounts, and everything when switching
is off, work exactly as before.

**How it knows.** The installer adds two small Hats hooks to Claude Code's settings:
one runs when a task finishes (`Stop`), one when a turn ends with an error
(`StopFailure`). They print nothing, and do nothing unless this chat is one Hats is
watching.

## When it never happens

- Switching is **off**.
- The account in use is under **Never switch to or from**.
- Fewer than two accounts take turns.
- `hat run <account>` and `hat exec <account> …`: you named the account yourself.
- `claude auth`, `claude mcp`, `claude config`, `claude --version` and similar.
- `claude` started from inside a Claude Code session keeps that session's account.
- Asking about a chat needs a terminal. In scripts, `claude -p` can switch at start,
  but nothing is ever asked.

## What you see while it works

- **Your prompt** keeps showing **this folder's account** (or the one you picked).
  That is the account `claude` *tries first*; it doesn't change when a chat moves.
- **Claude's status line** always shows the account Claude is **really** using.
  After a switch, that is where you'll see `work`.
- **The yellow `hat:` lines** say every time work moves, and why.
- **`hat status`** ends with a line such as
  `Automatic switching: on · moves on below 10% left · personal → work`.

## Work, client and personal accounts

Only put accounts under **Take turns** whose work is allowed to run on each other's
access. If an employer or client wants their work on their own account, leave that
account under **Never switch to or from**: their work stays on it even when it is low,
and other work never moves onto it.

## Without the screen

```bash
hat settings                          # the screen (in a script: prints it once)
hat settings switch on                # or: off
hat settings level 10                 # an account is low below 10% left (5 to 50)
hat settings order personal work      # who takes turns, top first; the rest never switch
hat settings order                    # nobody takes turns
```

They are stored in `~/.config/hats/hats.conf`:

```
switch on
switch_left 10
order personal work
```

`hat status --json` reports them as
`"switching": {"on": true, "left_below": 10, "order": ["personal", "work"]}`.

## Questions

**It didn't switch. Why?** Open `hat settings` and read the **Now:** line. Then check:

- Is it `[ on ]`?
- Is the account in use under **Take turns**? The prompt shows which one it is.
- Is it really low? Its **left now** may be old ([why](#what-low-means-exactly)).
- Does another account in Take turns have room and is it signed in?
- For a chat: was Claude started with `claude` in a normal terminal (not `hat run`)?
  Are the Hats hooks in `~/.claude/settings.json`? Run `python3 install.py` again to add them.

**It says "no usage yet".** Hats hasn't seen that account used in Claude Code on this
computer. Start `claude` on it once (`hat run work`) and the numbers appear.

**Will it go back to my first account later?** Yes, for new chats. Once personal has
room again (for example after its 5-hour reset), the next `claude` starts on
personal again, because it is first in the list. A chat that moved to work stays on
work.

**Can I move a chat by hand, without waiting until an account is low?** Yes:
`hat run work --resume`, then pick the chat.

**How do I turn it off?** `hat settings`, then Space on the first line (or
`hat settings switch off`). Your list is kept for next time.
