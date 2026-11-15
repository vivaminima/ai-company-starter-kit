# Acme Studio: company rules

Acme Studio is a made-up one-person business that sells printable planners. Everything in this folder is sample data. Replace it with your own when you are ready.

## How the company works

- Each department is a folder: `HQ/`, `Research/`, `Shop/`.
- One Claude window works as one department at a time. It becomes that department by reading the department's `CLAUDE.md`.
- Departments talk through files. A window never assumes it knows what another window did; it reads the file.
- The owner is the human. Departments propose, the owner decides.

## Sending a task

1. Copy `templates/task.md` into the other department's `_inbox/`. Name it `YYYY-MM-DD_from-<Sender>_<short-title>.md`.
2. Fill in every field. "Done when" must be something a person can check by opening a file.
3. Add one line about it under "Waiting on" in your own `_status/progress.md`.

## Doing a task

1. Take the oldest file in your `_inbox/`. Files in `_inbox/done/` are finished; leave them.
2. Do the work. Save what you make in your own `output/` folder.
3. Reply: copy `templates/reply.md` into the sender's `_inbox/`. Name it `YYYY-MM-DD_from-<You>_re-<short-title>.md`. Give the path of every file you made.
4. Move the task file into your `_inbox/done/`.
5. Update your `_status/progress.md`.

## Rules for every department

- Write only inside your own folder. The one exception is a new file in another department's `_inbox/`.
- Never edit, move or delete another department's files.
- Say what you did and what you did not do. If you could not finish, say so in the reply and in your progress file.
- If a task is unclear, reply with a question. Do not guess.
- Do not invent facts, numbers or sources. If the answer is not in the files you were given, say that.
- Keep `_status/progress.md` true. Someone opening it cold should know what is happening.
