#!/usr/bin/env python3
"""Seed data/book-of-serenity/NN.toml from the archived CBETA TEI.

Each case is a <head>第N則[Title]</head> (so we get a Chinese title too),
followed by Wansong's instruction (示眾), the case (本則, opening with 舉), and
Hongzhi's verse (頌, an <lg>). Commentary and capping phrases are omitted — see
CLAUDE.md. Merge-safe: refreshes only the original (zh) fields and the source
title, never translations or pointers.
"""
import os
import re
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbeta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources", "book-of-serenity.t48n2004.tei.xml")
OUT = os.path.join(ROOT, "data", "book-of-serenity")

# Most case headings read 第N則[Title]; a handful omit the 則, e.g. 第十三臨際瞎驢.
HEAD_RE = re.compile(r"^第([〇零一二三四五六七八九十百千]+)則?(.*)$")


def basic(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lit(s):
    assert "'''" not in s, "content contains triple-quote"
    return "'''\n" + s + "\n'''" if s else "'''\n'''"


def segment():
    _, body, gaiji = cbeta.parse(SRC)
    cases = {}
    cur = None
    for kind, rend, text in cbeta.blocks(body, gaiji):
        if kind == "head":
            m = HEAD_RE.match(text)
            if m:
                n = cbeta.cjk_num(m.group(1))
                cur = {"num": n, "title_zh": m.group(2).strip(), "intro": "",
                       "case": "", "verse_lg": [], "verse_p": []}
                cases[n] = cur
            continue
        if cur is None:
            continue
        if kind == "lg":
            if text.strip():
                cur["verse_lg"].append(text)
            continue
        # kind == "p"
        if text.startswith("示眾") and not cur["intro"]:
            cur["intro"] = re.sub(r"^示眾[云：。\s]*", "", text)
        elif "margin-left" in rend and text.startswith("舉") and not cur["case"]:
            cur["case"] = re.sub(r"^舉[。：\s]*", "", text)
        elif "margin-left" in rend and text.strip():
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
        f"title_zh = {basic(c['title_zh'])}",
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
    missing = [n for n in range(1, 101) if n not in cases]
    no_case = sorted(n for n, c in cases.items() if not c["case"].strip())
    no_verse = sorted(n for n, c in cases.items() if not c["verse"].strip())
    print(f"Wrote {len(cases)} cases. Missing: {missing or 'none'}")
    print(f"empty case: {no_case or 'none'} | empty verse: {no_verse or 'none'}")
    for n in (1, 100):
        if n in cases:
            c = cases[n]
            print(f"\n--- case {n}: {c['title_zh']} ---")
            print(f"intro({len(c['intro'])}): {c['intro'][:46]}")
            print(f"case ({len(c['case'])}): {c['case'][:46]}")
            print(f"verse:\n{c['verse'][:70]}")


if __name__ == "__main__":
    main()
