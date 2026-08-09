"""Tests for scripts/lint_data.py.

The fixtures in tests/fixtures/<rule>/data/ deliberately break exactly one rule
each; the suite asserts that only that rule fires. A final gate runs the linter
over the real data/ tree and requires exit 0.
"""

import os
import re
import subprocess
import sys
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
LINT = os.path.join(REPO, "scripts", "lint_data.py")
FIXTURES = os.path.join(TESTS, "fixtures")
DATA = os.path.join(REPO, "data")

# rule name -> the set of rules a clean run over that fixture must fire
FIXTURE_RULES = {
    "parse_error": {"parse_error"},
    "missing_required": {"missing_required"},
    "empty_case_zh": {"empty_case_zh"},
    "number_unique": {"number_unique"},
    "slug_unique": {"slug_unique"},
    "slug_matches_filename": {"slug_matches_filename"},
}

VIOLATION_LINE = re.compile(r"^.+: (\w+): .+$")


def run_linter(root):
    return subprocess.run(
        [sys.executable, LINT, "--root", root],
        capture_output=True, text=True, cwd=REPO,
    )


def rules_fired(stdout):
    rules = set()
    for line in stdout.splitlines():
        m = VIOLATION_LINE.match(line)
        if m:
            rules.add(m.group(1))
    return rules


class TestNegativeFixtures(unittest.TestCase):
    def test_fixtures_each_fire_exactly_their_rule(self):
        for name, expected in FIXTURE_RULES.items():
            with self.subTest(fixture=name):
                root = os.path.join(FIXTURES, name, "data")
                proc = run_linter(root)
                self.assertNotEqual(proc.returncode, 0,
                                    f"expected a nonzero exit for {name}: {proc.stdout}")
                fired = rules_fired(proc.stdout)
                self.assertEqual(fired, expected,
                                 f"{name} fired {sorted(fired)}; expected only {sorted(expected)}")


class TestPositiveGate(unittest.TestCase):
    def test_real_data_passes(self):
        proc = run_linter(DATA)
        self.assertEqual(proc.returncode, 0,
                         f"real data must lint clean (exit {proc.returncode}):\n"
                         f"{proc.stdout}\n{proc.stderr}")


if __name__ == "__main__":
    unittest.main()
