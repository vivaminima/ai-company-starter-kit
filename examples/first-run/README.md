# A real first run

These are the files that one real run of the three sentences in `START_HERE.md` produced, copied here unedited. The run was made on 2026-11-12 on an untouched copy of this kit. Each sentence was given to a fresh Claude Code agent session that had seen nothing but the folder.

Your run will not match word for word. Use these to see the shape of a finished round.

| After sentence | File | What it is |
| --- | --- | --- |
| 1 | `Research/_inbox/done/2026-11-12_from-HQ_december-newsletter-pick.md` | The task HQ wrote. It sat in `Research/_inbox/` until sentence 2 moved it to `done/`. |
| 2 | `Research/output/2026-11-12_december-newsletter-pick.md` | Research's result: one pick, three reasons with line references, and its own judgement kept apart. |
| 2 | `HQ/_inbox/done/2026-11-12_from-Research_re-december-newsletter-pick.md` | Research's reply to HQ. It sat in `HQ/_inbox/` until sentence 3 moved it to `done/`. |
| 2 | `Research/_status/progress.md` | Research's progress page after the task. |
| 3 | `HQ/_status/progress.md` | HQ's progress page at the end: the result is under "Done" and the choice is under "Needs the owner". |

Things worth noticing in the run:

- HQ did not invent a task. It took the one waiting under "Next" in its progress page.
- Research said what the product list does not contain, and put its own opinion under "My read".
- HQ opened the result file and checked it against "Done when" before calling it done.
- Nobody decided for the owner. The final choice is listed under "Needs the owner".

The checker's verdict on the folder after the run (`python tools/check_kit.py --first-run`):

```
AI Company Starter Kit, first-run check 1.0.0

  OK    1. task sent         Research has 0 waiting and 1 finished task file(s)
  OK    2. task done         1 result file(s) in Research/output/, 1 reply file(s) in HQ/_inbox/ or its done/ folder
  OK    3. result recorded   HQ/_status/progress.md lists 1 finished item(s) under Done

Result: PASS (3 check(s) passed, 0 failed)
```
