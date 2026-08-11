#!/usr/bin/env python3
"""Lint every data/<collection>/*.toml file so malformed data never reaches the build.

Checks mirror exactly what build.py reads (no invented fields):

  * the file parses as TOML                          (parse_error)
  * required keys are present
      - case files:          number, case_zh         (missing_required)
      - collection.toml:     slug, title_en, title_zh, compiler, date
  * within a collection, case numbers are unique     (number_unique)
  * within a collection, non-empty slugs are unique  (slug_unique)
  * a case's identity matches its filename: the numeric
    filename prefix equals the `number` field, and any slug
    written into the filename equals the `slug` field; for
    collection.toml the slug must match its directory name
                                                      (slug_matches_filename)
  * case_zh is present and non-empty                 (empty_case_zh)

Each violation is printed as:

    <path>: <rule>: <message>

The exit code is nonzero if anything fired, with a summary count on the
way out. Zero dependencies (Python stdlib only), same constraint as build.py.
"""

import argparse
import dataclasses
import os
import re
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROOT = os.path.join(ROOT, "data")

# The fields build.py indexes directly (c["number"], c["case_zh"],
# meta["slug"], meta["title_en"], ...). Everything else it reads via .get(),
# so it must not be required here.
REQUIRED_CASE_KEYS = ("number", "case_zh")
REQUIRED_COLLECTION_KEYS = ("slug", "title_en", "title_zh", "compiler", "date")

# A case file is "digits[(-slug)].toml", mirroring build.py's \d+\.toml scan
# plus an optional slug component for collections that name their files.
CASE_FILENAME_RE = re.compile(r"^(\d+)(?:-([a-z0-9-]+))?\.toml$")


@dataclasses.dataclass
class Violation:
    path: str
    rule: str
    message: str


def _collection_dirs(root):
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if os.path.isdir(d) and any(f.endswith(".toml") for f in os.listdir(d)):
            yield d, name


def _check_collection(path, cdir_name, data):
    v = []
    for key in REQUIRED_COLLECTION_KEYS:
        if key not in data:
            v.append(Violation(path, "missing_required",
                               f"missing required key '{key}'"))
    slug = data.get("slug")
    if slug and slug != cdir_name:
        v.append(Violation(path, "slug_matches_filename",
                           f"slug '{slug}' does not match directory name '{cdir_name}'"))
    return v


def _check_case(path, data):
    v = []
    for key in REQUIRED_CASE_KEYS:
        if key not in data:
            v.append(Violation(path, "missing_required",
                               f"missing required key '{key}'"))
    case_zh = data.get("case_zh")
    if case_zh is not None and not str(case_zh).strip():
        v.append(Violation(path, "empty_case_zh", "case_zh is empty"))

    num = data.get("number")
    slug = data.get("slug") or ""
    if isinstance(num, int):
        m = CASE_FILENAME_RE.match(os.path.basename(path))
        if m:
            prefix = int(m.group(1))
            if prefix != num:
                v.append(Violation(path, "slug_matches_filename",
                                   f"filename number {prefix} does not match number field {num}"))
            file_slug = m.group(2)
            if file_slug is not None and slug and file_slug != slug:
                v.append(Violation(path, "slug_matches_filename",
                                   f"filename slug '{file_slug}' does not match slug field '{slug}'"))
    return v, (path, num, slug or None)


def _check_uniqueness(cases):
    v = []
    seen_num = {}
    for path, num, _ in cases:
        if num is None:
            continue
        if num in seen_num:
            v.append(Violation(path, "number_unique",
                               f"number {num} already used by {seen_num[num]}"))
        else:
            seen_num[num] = path
    seen_slug = {}
    for path, _, slug in cases:
        if not slug:
            continue
        if slug in seen_slug:
            v.append(Violation(path, "slug_unique",
                               f"slug '{slug}' already used by {seen_slug[slug]}"))
        else:
            seen_slug[slug] = path
    return v


def _lint_collection(cdir, cdir_name):
    v = []
    cases = []
    for fname in sorted(os.listdir(cdir)):
        if not fname.endswith(".toml"):
            continue
        path = os.path.join(cdir, fname)
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError, ValueError) as e:
            v.append(Violation(path, "parse_error", str(e)))
            continue
        if fname == "collection.toml":
            v += _check_collection(path, cdir_name, data)
        else:
            cv, case = _check_case(path, data)
            v += cv
            if case is not None:
                cases.append(case)
    v += _check_uniqueness(cases)
    return v


def lint_tree(root):
    """Return every violation found under root (a data/ tree)."""
    violations = []
    for cdir, cdir_name in _collection_dirs(root):
        violations += _lint_collection(cdir, cdir_name)
    return violations


def report(violations, out=None):
    """Print each violation and a summary; return the process exit code."""
    out = out if out is not None else sys.stdout
    for vio in sorted(violations, key=lambda v: (v.path, v.rule)):
        print(f"{vio.path}: {vio.rule}: {vio.message}", file=out)
    n_files = len({vio.path for vio in violations})
    n_rules = len({vio.rule for vio in violations})
    if violations:
        print(f"lint_data: {len(violations)} violation(s) across {n_files} file(s), "
              f"{n_rules} rule(s) fired — fix before building.", file=out)
    else:
        print("lint_data: clean", file=out)
    return 1 if violations else 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Lint data/*/*.toml so malformed data never reaches the site build.")
    ap.add_argument("--root", default=DEFAULT_ROOT,
                    help=f"data tree to lint (default: {DEFAULT_ROOT})")
    args = ap.parse_args(argv)
    return report(lint_tree(args.root))


if __name__ == "__main__":
    sys.exit(main())
