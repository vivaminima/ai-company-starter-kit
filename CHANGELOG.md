# Changelog

## 1.0.1 - 2026-11-13

- The product name is now "AI Company Starter Kit". The README says in plain words that the kit is used with the Claude desktop app.
- No change to the sample company, the checker or the skill.

## 1.0.0 - 2026-11-13

First release.

- Sample company "Acme Studio" with three departments (`HQ/`, `Research/`, `Shop/`), each with a role file, an inbox and a progress page.
- Company rules in `CLAUDE.md`: how to send a task, how to do one, what each department may write.
- `START_HERE.md`: three sentences that take the company through one full round.
- `examples/first-run/`: the files a real run of those sentences produced.
- `templates/task.md` and `templates/reply.md`.
- `tools/check_kit.py`: read-only structure check (departments, inbox and status, CLAUDE.md size, links, starter sentences, optional banned-word list, first-run check).
- `skills/beginner-readme-section/`: Claude Code skill that writes a "New to this? Start here" section for a README.
- 30 unit tests for the checker.
