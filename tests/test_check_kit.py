"""Tests for tools/check_kit.py. Run from the kit folder:

    python -m unittest discover -s tests -v
"""
import locale
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
SCRIPT = os.path.join(KIT, "tools", "check_kit.py")
sys.path.insert(0, os.path.join(KIT, "tools"))

import check_kit as ck  # noqa: E402


class Case(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="kit test "))
        self.addCleanup(shutil.rmtree, self.root, True)

    def write(self, name, text="x\n"):
        path = os.path.join(self.root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        return path

    def make_kit(self, departments=("HQ", "Research")):
        self.write("CLAUDE.md", "# Rules\n")
        self.write("START_HERE.md",
                   "# Start\n\n```\nRead HQ/CLAUDE.md and send a task through Research/_inbox.\n```\n")
        for name in departments:
            self.write("%s/CLAUDE.md" % name, "# %s\n" % name)
            self.write("%s/_inbox/.gitkeep" % name, "")
            self.write("%s/_status/progress.md" % name,
                       "# progress\nLast updated: not yet (sample starting state)\n")

    def run_script(self, args=(), env=None):
        environ = dict(os.environ)
        for name in ("PYTHONIOENCODING", "PYTHONUTF8"):
            environ.pop(name, None)
        if sys.flags.utf8_mode:
            environ["PYTHONUTF8"] = "1"
        environ.update(env or {})
        proc = subprocess.run([sys.executable, SCRIPT, self.root] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environ)
        encoding = environ.get("PYTHONIOENCODING") or locale.getpreferredencoding(False)
        return (proc.returncode, proc.stdout.decode(encoding, "replace"),
                proc.stderr.decode(encoding, "replace"))

    def row(self, out, name):
        for line in out.splitlines():
            if name in line and line.strip().split()[0] in ("OK", "FAIL", "--"):
                return line.strip()
        self.fail("no row for %r in:\n%s" % (name, out))


class Structure(Case):
    def test_good_kit_passes(self):
        self.make_kit()
        code, out, err = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn("2 found: HQ, Research", out)
        self.assertIn("Result: PASS (5 check(s) passed, 0 failed)", out)
        self.assertEqual(err, "")

    def test_no_departments(self):
        self.write("CLAUDE.md", "# Rules\n")
        self.write("START_HERE.md", "```\nhello\n```\n")
        code, out, err = self.run_script()
        self.assertEqual(code, 1)
        self.assertTrue(self.row(out, "departments").startswith("FAIL"))

    def test_missing_inbox_and_progress(self):
        self.make_kit()
        shutil.rmtree(os.path.join(self.root, "Research", "_inbox"))
        os.remove(os.path.join(self.root, "HQ", "_status", "progress.md"))
        code, out, err = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("- Research/_inbox/ is missing", out)
        self.assertIn("- HQ/_status/progress.md is missing", out)

    def test_nested_departments_are_found(self):
        self.make_kit()
        self.write("department-templates/Marketing/CLAUDE.md", "# M\n")
        self.write("department-templates/Marketing/_inbox/.gitkeep", "")
        self.write("department-templates/Marketing/_status/progress.md", "p\n")
        code, out, err = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn("3 found: HQ, Research, department-templates/Marketing", out)

    def test_folder_with_korean_and_spaces(self):
        self.make_kit(("본부", "연구 팀"))
        self.write("START_HERE.md", "```\nhello\n```\n")
        code, out, err = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn("본부", out)

    def test_no_absolute_paths_in_output(self):
        self.make_kit()
        self.write("HQ/notes.md", "[gone](missing.md)\n")
        code, out, err = self.run_script()
        self.assertNotIn(self.root, out)
        self.assertNotRegex(out, r"[A-Za-z]:[\\/]|/Users/|/home/|/tmp/")


class Sizes(Case):
    def test_estimate(self):
        self.assertEqual(ck.estimate_tokens(""), 0)
        self.assertEqual(ck.estimate_tokens("abcd" * 100), 100)
        self.assertEqual(ck.estimate_tokens("한글" * 10), 30)

    def test_oversized_claude_md_fails(self):
        self.make_kit()
        self.write("Research/CLAUDE.md", "word " * 4000)
        code, out, err = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("1 file(s) over the limit of 4000 tokens", out)
        self.assertIn("- Research/CLAUDE.md is about 5000 tokens", out)

    def test_max_tokens_option(self):
        self.make_kit()
        self.write("HQ/CLAUDE.md", "word " * 100)
        self.assertEqual(self.run_script(["--max-tokens", "200"])[0], 0)
        self.assertEqual(self.run_script(["--max-tokens", "100"])[0], 1)


class Links(Case):
    def test_broken_link_is_reported_with_file_and_line(self):
        self.make_kit()
        self.write("HQ/notes.md", "ok [a](CLAUDE.md)\n\nbad [b](../Shop/products.md)\n")
        code, out, err = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("2 relative link(s), 1 broken", out)
        self.assertIn("- HQ/notes.md:3: ../Shop/products.md", out)

    def test_links_that_are_not_checked(self):
        self.make_kit()
        self.write("doc.md", "\n".join([
            "[web](%s://example.com/x) [mail](mailto:a@example.com) [top](#start)" % "https",
            "[anchor](CLAUDE.md#rules) [spaced](my%20file.md) ![image](missing.png)",
            "`[in code](nope.md)` [placeholder]({{PATH}}/x.md)",
            "```",
            "[fenced](nope.md)",
            "```",
        ]))
        self.write("my file.md")
        code, out, err = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn("2 relative link(s), 0 broken", out)


class StartHere(Case):
    def test_missing_file(self):
        self.make_kit()
        os.remove(os.path.join(self.root, "START_HERE.md"))
        code, out, err = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("START_HERE.md is missing", out)

    def test_sentence_naming_a_missing_path(self):
        self.make_kit()
        self.write("START_HERE.md", "# Start\n\n```\nRead HQ/CLAUDE.md.\n```\n\ntext\n\n"
                                    "```\nSend it through Shop/_inbox and tools/x.py.\n```\n")
        code, out, err = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("2 block(s), 3 path(s), 2 missing", out)
        self.assertIn("- START_HERE.md:10: Shop/_inbox", out)
        self.assertIn("- START_HERE.md:10: tools/x.py", out)

    def test_full_stop_after_a_path_is_not_part_of_it(self):
        self.make_kit()
        self.write("START_HERE.md", "```\nRead HQ/CLAUDE.md. Then use Nope/_inbox.\n```\n")
        code, out, err = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("- START_HERE.md:2: Nope/_inbox\n", out.replace("\r\n", "\n"))

    def test_no_fenced_sentences(self):
        self.make_kit()
        self.write("START_HERE.md", "Read HQ/CLAUDE.md\n")
        code, out, err = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("has no fenced sentences", out)


class Banned(Case):
    def test_no_list(self):
        self.make_kit()
        self.assertTrue(self.row(self.run_script()[1], "banned words").startswith("--"))

    def test_hits_and_no_hits(self):
        self.make_kit()
        words = self.write("words.txt", "# my list\nSecret Client\n\n비밀\n")
        outside = os.path.join(os.path.dirname(self.root), os.path.basename(self.root) + ".txt")
        shutil.move(words, outside)
        self.addCleanup(lambda: os.path.exists(outside) and os.remove(outside))
        code, out, err = self.run_script(["--banned", outside])
        self.assertEqual(code, 0, out)
        self.assertIn("2 word(s) in the list, 0 hits", out)
        self.write("HQ/notes.md", "one\nfor the secret client only\n비밀 문서\n")
        code, out, err = self.run_script(["--banned", outside])
        self.assertEqual(code, 1)
        self.assertIn("2 hit(s)", out)
        self.assertIn("- HQ/notes.md:2: secret client", out)

    def test_list_inside_the_kit_is_not_scanned(self):
        self.make_kit()
        words = self.write("tools/banned_words.txt", "forbidden\n")
        self.assertEqual(self.run_script(["--banned", words])[0], 0)

    def test_missing_list_is_a_usage_error(self):
        self.make_kit()
        code, out, err = self.run_script(["--banned", os.path.join(self.root, "nope.txt")])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")


class FirstRun(Case):
    def make_sample(self):
        self.make_kit(("HQ", "Research", "Shop"))
        self.write("Research/output/.gitkeep", "")
        self.write("Research/_inbox/done/.gitkeep", "")

    def test_nothing_done_yet(self):
        self.make_sample()
        code, out, err = self.run_script(["--first-run"])
        self.assertEqual(code, 1)
        self.assertIn("Result: FAIL (0 check(s) passed, 3 failed)", out)
        self.assertIn("use sentence 1 in START_HERE.md", out)

    def test_after_sentence_1(self):
        self.make_sample()
        self.write("Research/_inbox/2026-01-05_from-HQ_pick.md")
        code, out, err = self.run_script(["--first-run"])
        self.assertEqual(code, 1)
        self.assertTrue(self.row(out, "1. task sent").startswith("OK"))
        self.assertTrue(self.row(out, "2. task done").startswith("FAIL"))

    def test_after_sentence_2(self):
        self.make_sample()
        self.write("Research/_inbox/done/2026-01-05_from-HQ_pick.md")
        self.write("Research/output/2026-01-05_pick.md")
        self.write("HQ/_inbox/2026-01-05_from-Research_re-pick.md")
        code, out, err = self.run_script(["--first-run"])
        self.assertEqual(code, 1)
        self.assertTrue(self.row(out, "2. task done").startswith("OK"))
        self.assertTrue(self.row(out, "3. result recorded").startswith("FAIL"))

    def test_whole_round(self):
        self.make_sample()
        self.write("Research/_inbox/done/2026-01-05_from-HQ_pick.md")
        self.write("Research/output/2026-01-05_pick.md")
        self.write("HQ/_inbox/done/2026-01-05_from-Research_re-pick.md")
        self.write("HQ/_status/progress.md", "# HQ progress\nLast updated: 2026-01-05\n\n"
                                             "## Waiting on\n- Research: the pick\n\n"
                                             "## Done\n- Nothing yet.\n")
        code, out, err = self.run_script(["--first-run"])
        self.assertEqual(code, 1, out)
        self.assertTrue(self.row(out, "3. result recorded").startswith("FAIL"))
        self.write("HQ/_status/progress.md", "# HQ progress\nLast updated: 2026-01-05\n\n"
                                             "## Done\n\n- Research picked the goal planner.\n\n"
                                             "## Notes\n- other\n")
        code, out, err = self.run_script(["--first-run"])
        self.assertEqual(code, 0, out)
        self.assertIn("lists 1 finished item(s) under Done", out)
        self.assertIn("Result: PASS (3 check(s) passed, 0 failed)", out)


class Cli(Case):
    def test_not_a_folder(self):
        proc = subprocess.run([sys.executable, SCRIPT, os.path.join(self.root, "nope")],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 2)

    def test_cp949_console(self):
        self.make_kit(("HQ", "café ✅"))
        self.write("START_HERE.md", "```\nRead HQ/CLAUDE.md.\n```\n")
        code, out, err = self.run_script(env={"PYTHONIOENCODING": "cp949"})
        self.assertEqual(code, 0, out)
        self.assertNotIn("Traceback", err)

    def test_checker_writes_nothing(self):
        self.make_kit()
        before = sorted(ck.walk_files(self.root))
        self.run_script()
        self.run_script(["--first-run"])
        self.assertEqual(sorted(ck.walk_files(self.root)), before)

    def test_version(self):
        proc = subprocess.run([sys.executable, SCRIPT, "--version"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertIn(ck.__version__.encode(), proc.stdout)


class ShippedKit(unittest.TestCase):
    """The kit this test file ships in must pass its own check."""

    def test_this_kit_passes(self):
        proc = subprocess.run([sys.executable, SCRIPT], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        out = proc.stdout.decode(locale.getpreferredencoding(False), "replace")
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("0 failed", out)

    def test_departments_of_the_sample_company(self):
        found = ck.find_departments(KIT)
        for name in ("HQ", "Research", "Shop"):
            self.assertIn(name, found)

    def test_every_claude_md_is_small(self):
        for path in ck.walk_files(KIT):
            if os.path.basename(path) == "CLAUDE.md":
                self.assertLessEqual(ck.estimate_tokens(ck.read_text(path)), 4000, path)


if __name__ == "__main__":
    unittest.main()
