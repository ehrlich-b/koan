#!/usr/bin/env python3
"""Seed data/blue-cliff-record/NN.toml from the archived CBETA TEI.

Core depth: each case keeps the introduction (垂示), the case proper (本則,
introduced by 舉), and Xuedou's verse (頌). Yuanwu's prose commentary (評唱) and
the interlinear capping phrases (著語) are intentionally left out — see CLAUDE.md.

Merge-safe: refreshes only the original (zh) fields; never touches translations,
titles, or pointers already written by hand.
"""
import os
import re
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbeta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources", "blue-cliff-record.t48n2003.tei.xml")
OUT = os.path.join(ROOT, "data", "blue-cliff-record")

# A case paragraph opens with a bracketed numeral, e.g. 【一七】舉。 (= case 17).
# Numerals are positional digits: 一〇〇 = 100. (Case 42's 舉 marker is irregular
# in the source, so we key on the bracketed numeral alone, not on 舉.)
CASE_RE = re.compile(r"^【([〇零一二三四五六七八九十百]+)】")
DIGIT = {"〇": "0", "零": "0", "一": "1", "二": "2", "三": "3", "四": "4",
         "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}
PRESERVE = ("slug", "title_zh", "title_en", "intro_en", "case_en", "verse_en", "pointer")


def to_int(s):
    if all(c in DIGIT for c in s):
        return int("".join(DIGIT[c] for c in s))
    units = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
             "八": 8, "九": 9}
    if s == "百":
        return 100
    if "十" in s:
        a, _, b = s.partition("十")
        return (units.get(a, 1)) * 10 + (units.get(b, 0) if b else 0)
    return units.get(s, 0)


def basic(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lit(s):
    assert "'''" not in s, "content contains triple-quote"
    return "'''\n" + s + "\n'''" if s else "'''\n'''"


def segment():
    _, body, gaiji = cbeta.parse(SRC)
    cases = {}
    pending_intro = ""
    cur = None
    for kind, rend, text in cbeta.blocks(body, gaiji):
        if kind == "lg":
            if cur is not None and text.strip():
                cur["verse_lg"].append(text)
            continue
        if text.startswith("垂示云"):
            pending_intro = re.sub(r"^垂示云[。\s]*", "", text)
            continue
        m = CASE_RE.match(text)
        if m:
            n = to_int(m.group(1))
            body_text = re.sub(r"^舉[。：\s]*", "", text[m.end():])
            cur = {"num": n, "intro": pending_intro, "case": body_text,
                   "verse_lg": [], "verse_p": []}
            cases[n] = cur
            pending_intro = ""
            continue
        # A few early cases store the verse as an indented <p> instead of <lg>.
        # Collect indented non-case quote blocks as a fallback verse source.
        if cur is not None and "margin-left" in rend and text.strip():
            cur["verse_p"].append(text)
    for c in cases.values():
        c["verse"] = "\n".join(c["verse_lg"] or c["verse_p"])
    return cases


def write_case(c):
    path = os.path.join(OUT, f"{c['num']:03d}.toml")
    old = {}
    if os.path.exists(path):
        with open(path, "rb") as f:
            old = tomllib.load(f)
    g = lambda k, d="": old.get(k, d)
    out = [
        f"number = {c['num']}",
        f"slug = {basic(g('slug'))}",
        f"title_zh = {basic(g('title_zh'))}",
        f"title_en = {basic(g('title_en'))}",
        "",
        f"intro_zh = {lit(c['intro'])}",
        f"intro_en = {lit(g('intro_en'))}",
        "",
        f"case_zh = {lit(c['case'])}",
        f"case_en = {lit(g('case_en'))}",
        "",
        f"verse_zh = {lit(c['verse'])}",
        f"verse_en = {lit(g('verse_en'))}",
        "",
        f"pointer = {lit(g('pointer'))}",
        "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def main():
    os.makedirs(OUT, exist_ok=True)
    cases = segment()
    for c in cases.values():
        write_case(c)
    for c in cases.values():
        with open(os.path.join(OUT, f"{c['num']:03d}.toml"), "rb") as f:
            tomllib.load(f)
    found = sorted(cases)
    missing = [n for n in range(1, 101) if n not in cases]
    print(f"Wrote {len(found)} cases. Missing: {missing or 'none'}")
    for n in (1, 42, 100):
        if n in cases:
            c = cases[n]
            print(f"\n--- case {n} ---")
            print(f"intro({len(c['intro'])}): {c['intro'][:50]}")
            print(f"case ({len(c['case'])}): {c['case'][:50]}")
            print(f"verse:\n{c['verse'][:80]}")


if __name__ == "__main__":
    main()
