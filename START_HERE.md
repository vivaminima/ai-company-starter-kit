# Start here

Three sentences take the sample company through one full round: HQ sends a task, Research does it, HQ records the result. Nothing leaves your computer except your conversation with Claude; the company itself is only files in this folder.

Before you begin: open this folder in the Claude desktop app, in the Code tab. Each sentence below goes into the message box as it is.

## 1. HQ sends a task

```
Read HQ/CLAUDE.md and act as the HQ lead. Send one task to Research through Research/_inbox.
```

What to look for: one new file in `Research/_inbox/`, named with today's date and `from-HQ`. HQ takes the task from the "Next" list in `HQ/_status/progress.md`.

## 2. Research does the task

For the real multi-window feel, start a new session in the same folder for this one. It also works in the same window.

```
Read Research/CLAUDE.md and act as the Research lead. Do the oldest task in Research/_inbox and reply to the sender.
```

What to look for: a result file in `Research/output/`, a reply in `HQ/_inbox/`, and the task moved to `Research/_inbox/done/`.

## 3. HQ records the result

```
Read HQ/CLAUDE.md and act as the HQ lead. Read the replies in HQ/_inbox and update HQ/_status/progress.md.
```

What to look for: `HQ/_status/progress.md` now lists the task under "Done" and says what Research found.

## Check the round

Ask Claude:

```
List the files in Research/output and HQ/_inbox, and show me HQ/_status/progress.md.
```

Or, if you have Python 3.8 or newer, run the checker. It only reads files.

```
python tools/check_kit.py --first-run
```

## What next

- Give Shop a task the same way: tell HQ what you want, and let HQ send it through `Shop/_inbox`.
- Make it yours: change the company description in `CLAUDE.md`, replace `Shop/products.md`, rename the departments.
- Add a department: copy one department folder, rename it, rewrite its `CLAUDE.md`, and add a row to the table in `HQ/CLAUDE.md`. Run `python tools/check_kit.py` afterwards.
- The rules every department follows are in [CLAUDE.md](CLAUDE.md). The message formats are [templates/task.md](templates/task.md) and [templates/reply.md](templates/reply.md).
