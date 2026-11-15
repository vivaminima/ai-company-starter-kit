#!/usr/bin/env python3
"""check_kit.py: structure check for an AI Company Starter Kit folder.

Reads the folder and reports:
  * which departments exist (a department is a folder with a CLAUDE.md)
  * whether each one has _inbox/ and _status/progress.md
  * the estimated size of every CLAUDE.md, against a token limit
  * broken relative links in Markdown files
  * whether the paths named in START_HERE.md exist
  * words from your own banned-word list (optional)
  * whether the first-run round has happened (--first-run)

Standard library only. Makes no network requests. Reads files, writes none.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys

__version__ = "1.0.0"

DEFAULT_MAX_TOKENS = 4000
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
TEXT_EXTENSIONS = {".md", ".txt", ".py", ".json", ".toml", ".yml", ".yaml"}

_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_LINK_RE = re.compile(r"(?<!\!)\[[^\]\n]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"\n]*\")?\s*\)")
_PATH_TOKEN_RE = re.compile(r"(?<![\w/.\\-])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)/?")
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def harden_streams():
    """Never crash on a console that cannot print a character (cp949, cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except Exception:
            pass


def read_text(path):
    with open(path, "rb") as handle:
        raw = handle.read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def rel(path, root):
    return os.path.relpath(path, root).replace("\\", "/")


def walk_files(root):
    """Every file under root, skipping tool folders. Sorted."""
    found = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            found.append(os.path.join(folder, name))
    return found


def estimate_tokens(text):
    """Rough size: 4 characters per token for ASCII, 1.5 tokens per other character."""
    ascii_chars = sum(1 for char in text if ord(char) < 128)
    other_chars = len(text) - ascii_chars
    return int(math.ceil(ascii_chars / 4.0 + other_chars * 1.5))


def lines_outside_fences(text):
    """(line number, line) for lines that are not inside a fenced code block."""
    fence = ""
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if fence:
            if (stripped and stripped[0] == fence[0] and len(stripped) >= len(fence)
                    and stripped == stripped[0] * len(stripped)):
                fence = ""
            continue
        match = _FENCE_RE.match(line)
        if match:
            fence = match.group(1)
            continue
        yield number, line


def fenced_blocks(text):
    """The contents of each fenced code block, as (first line number, text)."""
    blocks = []
    fence = ""
    start = 0
    body = []
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if fence:
            if (stripped and stripped[0] == fence[0] and len(stripped) >= len(fence)
                    and stripped == stripped[0] * len(stripped)):
                blocks.append((start, "\n".join(body)))
                fence = ""
            else:
                body.append(line)
            continue
        match = _FENCE_RE.match(line)
        if match:
            fence = match.group(1)
            start = number + 1
            body = []
    return blocks


# ----------------------------------------------------------------- checks

def find_departments(root):
    """Folders below root that hold a CLAUDE.md, as paths relative to root."""
    found = []
    for path in walk_files(root):
        if os.path.basename(path) == "CLAUDE.md" and os.path.dirname(path) != root:
            found.append(rel(os.path.dirname(path), root))
    return sorted(found)


def check_departments(root):
    departments = find_departments(root)
    if not departments:
        return [("FAIL", "departments", "none found: no folder below the top has a CLAUDE.md", [])]
    rows = [("OK", "departments", "%d found: %s" % (len(departments), ", ".join(departments)), [])]
    problems = []
    for name in departments:
        base = os.path.join(root, name)
        if not os.path.isdir(os.path.join(base, "_inbox")):
            problems.append("%s/_inbox/ is missing" % name)
        if not os.path.isfile(os.path.join(base, "_status", "progress.md")):
            problems.append("%s/_status/progress.md is missing" % name)
    if problems:
        rows.append(("FAIL", "inbox and status", "%d problem(s)" % len(problems), problems))
    else:
        rows.append(("OK", "inbox and status",
                     "every department has _inbox/ and _status/progress.md", []))
    return rows


def check_sizes(root, limit):
    sizes = []
    for path in walk_files(root):
        if os.path.basename(path) == "CLAUDE.md":
            sizes.append((estimate_tokens(read_text(path)), rel(path, root)))
    if not sizes:
        return [("FAIL", "CLAUDE.md size", "no CLAUDE.md found", [])]
    over = ["%s is about %d tokens" % (name, size) for size, name in sorted(sizes) if size > limit]
    largest = max(sizes)
    if over:
        return [("FAIL", "CLAUDE.md size", "%d file(s) over the limit of %d tokens"
                 % (len(over), limit), over)]
    return [("OK", "CLAUDE.md size", "%d file(s); largest is %s, about %d tokens (limit %d)"
             % (len(sizes), largest[1], largest[0], limit), [])]


def check_links(root):
    total = 0
    broken = []
    for path in walk_files(root):
        if not path.lower().endswith(".md"):
            continue
        folder = os.path.dirname(path)
        for number, line in lines_outside_fences(read_text(path)):
            line = re.sub(r"`[^`]*`", "", line)
            for match in _LINK_RE.finditer(line):
                target = match.group(1)
                if _SCHEME_RE.match(target) or target.startswith("#"):
                    continue
                if "{{" in target or "<" in target:
                    continue
                target = target.split("#", 1)[0].replace("%20", " ")
                if not target:
                    continue
                total += 1
                if not os.path.exists(os.path.normpath(os.path.join(folder, target))):
                    broken.append("%s:%d: %s" % (rel(path, root), number, target))
    if broken:
        return [("FAIL", "links", "%d relative link(s), %d broken" % (total, len(broken)), broken)]
    return [("OK", "links", "%d relative link(s), 0 broken" % total, [])]


def check_start_here(root):
    path = os.path.join(root, "START_HERE.md")
    if not os.path.isfile(path):
        return [("FAIL", "starter sentences", "START_HERE.md is missing", [])]
    blocks = fenced_blocks(read_text(path))
    paths = []
    missing = []
    for start, body in blocks:
        for offset, line in enumerate(body.splitlines()):
            for match in _PATH_TOKEN_RE.finditer(line):
                token = match.group(1).rstrip(".")  # a sentence may end right after a path
                paths.append(token)
                if not os.path.exists(os.path.join(root, token)):
                    missing.append("START_HERE.md:%d: %s" % (start + offset, token))
    if not blocks:
        return [("FAIL", "starter sentences", "START_HERE.md has no fenced sentences", [])]
    if missing:
        return [("FAIL", "starter sentences", "%d block(s), %d path(s), %d missing"
                 % (len(blocks), len(paths), len(missing)), missing)]
    return [("OK", "starter sentences", "%d block(s), %d path(s), 0 missing"
             % (len(blocks), len(paths)), [])]


def load_banned(path):
    words = []
    for line in read_text(path).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.append(line)
    return words


def check_banned(root, list_path):
    if not list_path:
        return [("--", "banned words", "no list given (use --banned FILE)", [])]
    words = load_banned(list_path)
    if not words:
        return [("--", "banned words", "the list is empty", [])]
    pattern = re.compile("|".join(re.escape(word) for word in words), re.IGNORECASE)
    skip = os.path.normcase(os.path.abspath(list_path))
    hits = []
    for path in walk_files(root):
        if os.path.normcase(os.path.abspath(path)) == skip:
            continue
        if os.path.splitext(path)[1].lower() not in TEXT_EXTENSIONS:
            continue
        for number, line in enumerate(read_text(path).splitlines(), 1):
            match = pattern.search(line)
            if match:
                hits.append("%s:%d: %s" % (rel(path, root), number, match.group()))
    if hits:
        return [("FAIL", "banned words", "%d word(s) in the list, %d hit(s)"
                 % (len(words), len(hits)), hits)]
    return [("OK", "banned words", "%d word(s) in the list, 0 hits" % len(words), [])]


def _real_files(folder):
    """Files directly in a folder, ignoring placeholders such as .gitkeep."""
    if not os.path.isdir(folder):
        return []
    return sorted(name for name in os.listdir(folder)
                  if os.path.isfile(os.path.join(folder, name)) and not name.startswith("."))


def check_first_run(root):
    """Has the round in START_HERE.md happened? Looks at the sample departments."""
    steps = []
    waiting = _real_files(os.path.join(root, "Research", "_inbox"))
    finished = _real_files(os.path.join(root, "Research", "_inbox", "done"))
    results = _real_files(os.path.join(root, "Research", "output"))
    replies = (_real_files(os.path.join(root, "HQ", "_inbox"))
               + _real_files(os.path.join(root, "HQ", "_inbox", "done")))

    if waiting or finished:
        steps.append(("OK", "1. task sent", "Research has %d waiting and %d finished task file(s)"
                      % (len(waiting), len(finished)), []))
    else:
        steps.append(("FAIL", "1. task sent", "no task file in Research/_inbox/ yet: "
                      "use sentence 1 in START_HERE.md", []))
    if results and replies:
        steps.append(("OK", "2. task done", "%d result file(s) in Research/output/, "
                      "%d reply file(s) in HQ/_inbox/ or its done/ folder"
                      % (len(results), len(replies)), []))
    else:
        detail = []
        if not results:
            detail.append("no result file in Research/output/")
        if not replies:
            detail.append("no reply in HQ/_inbox/")
        steps.append(("FAIL", "2. task done", "; ".join(detail)
                      + ": use sentence 2 in START_HERE.md", []))
    progress = os.path.join(root, "HQ", "_status", "progress.md")
    text = read_text(progress) if os.path.isfile(progress) else ""
    done = done_entries(text)
    if done:
        steps.append(("OK", "3. result recorded", "HQ/_status/progress.md lists %d "
                      "finished item(s) under Done" % len(done), []))
    else:
        steps.append(("FAIL", "3. result recorded", "HQ/_status/progress.md has nothing "
                      "under Done yet: use sentence 3 in START_HERE.md", []))
    return steps


def done_entries(progress_text):
    """Lines under the "Done" heading of a progress file that record something."""
    entries = []
    inside = False
    for line in progress_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            inside = stripped.lstrip("#").strip().lower() == "done"
            continue
        if inside and stripped and not re.match(r"^[-*]?\s*nothing\b", stripped, re.IGNORECASE):
            entries.append(stripped)
    return entries


# ------------------------------------------------------------------- cli

def render(rows, title):
    lines = [title, ""]
    for status, name, summary, details in rows:
        lines.append("  %-5s %-20s %s" % (status, name, summary))
        for detail in details:
            lines.append("          - %s" % detail)
    failed = sum(1 for row in rows if row[0] == "FAIL")
    passed = sum(1 for row in rows if row[0] == "OK")
    lines.append("")
    lines.append("Result: %s (%d check(s) passed, %d failed)"
                 % ("FAIL" if failed else "PASS", passed, failed))
    return "\n".join(lines), failed


def build_parser():
    parser = argparse.ArgumentParser(
        prog="check_kit.py",
        description="Check the structure of an AI Company Starter Kit folder. "
                    "Reads files, changes nothing.",
    )
    parser.add_argument("folder", nargs="?", help="the company folder (default: "
                        "the folder above tools/)")
    parser.add_argument("--first-run", action="store_true",
                        help="check whether the three sentences in START_HERE.md "
                             "have been run")
    parser.add_argument("--banned", metavar="FILE",
                        help="a text file with one word or phrase per line that "
                             "must not appear in the kit")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help="size limit for each CLAUDE.md, estimated "
                             "(default: %d)" % DEFAULT_MAX_TOKENS)
    parser.add_argument("--version", action="version", version="check_kit " + __version__)
    return parser


def main(argv=None):
    harden_streams()
    args = build_parser().parse_args(argv)
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(args.folder) if args.folder else os.path.dirname(here)
    if not os.path.isdir(root):
        sys.stderr.write("check_kit: not a folder\n")
        return 2
    if args.banned and not os.path.isfile(args.banned):
        sys.stderr.write("check_kit: the banned-word list was not found\n")
        return 2

    if args.first_run:
        rows = check_first_run(root)
        title = "AI Company Starter Kit, first-run check %s" % __version__
    else:
        rows = (check_departments(root) + check_sizes(root, args.max_tokens)
                + check_links(root) + check_start_here(root)
                + check_banned(root, args.banned))
        title = "AI Company Starter Kit, structure check %s" % __version__
    text, failed = render(rows, title)
    print(text)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
