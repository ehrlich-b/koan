#!/usr/bin/env python3
"""Seed data/record-of-layman-pang/NNN.toml from the CBETA TEI (X1336).

The Record of Layman Pang (龐居士語錄, X1336) has three fascicles: the 語錄
(卷上) — Pang's biography and his encounter dialogues with the masters of his
day — and two fascicles of his poems (詩) plus later masters' verses in his
praise. We take the 語錄 prose: the opening life-record, then one passage per
encounter, exactly as the source paragraphs them. The poetry fascicles and the
later encomia are left out (noted in collection.toml).

CBETA apparatus is stripped by cbeta.py. Merge-safe: refreshes only the original
(zh) fields and the source title; never touches translations or pointers.
"""
import os
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbeta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources", "record-of-layman-pang.x69n1336.tei.xml")
OUT = os.path.join(ROOT, "data", "record-of-layman-pang")


def basic(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lit(s):
    assert "'''" not in s, "content contains triple-quote"
    return "'''\n" + s + "\n'''" if s else "'''\n'''"


def segment():
    _, body, gaiji = cbeta.parse(SRC)
    passages = []
    # The 語錄 (卷上) is the opening run of prose — Pang's life-record and then
    # his encounter dialogues. It ends where the first poem begins: the 詩
    # fascicles (卷中/卷下) and the later 雜句 / 歷代讚文 appendices that follow
    # are not his recorded sayings, so we stop at the first <lg>.
    for kind, rend, text in cbeta.blocks(body, gaiji):
        if kind == "lg":
            break
        if kind != "p" or not text.strip():
            continue
        passages.append({"case": text})
    for i, p in enumerate(passages, 1):
        p["num"] = i
        p["title_zh"] = "行狀" if i == 1 else ""
    return passages


def write_case(c):
    path = os.path.join(OUT, f"{c['num']:03d}.toml")
    old = {}
    if os.path.exists(path):
        with open(path, "rb") as f:
            old = tomllib.load(f)
    g = lambda k, d="": old.get(k, d)
    title_zh = g("title_zh") or c["title_zh"]
    out = [
        f"number = {c['num']}",
        f"slug = {basic(g('slug'))}",
        f"title_zh = {basic(title_zh)}",
        f"title_en = {basic(g('title_en'))}",
        "",
        f"intro_zh = {lit(g('intro_zh'))}",
        f"intro_en = {lit(g('intro_en'))}",
        "",
        f"case_zh = {lit(c['case'])}",
        f"case_en = {lit(g('case_en'))}",
        "",
        f"verse_zh = {lit(g('verse_zh'))}",
        f"verse_en = {lit(g('verse_en'))}",
        "",
        f"pointer = {lit(g('pointer'))}",
        "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def main():
    os.makedirs(OUT, exist_ok=True)
    passages = segment()
    for c in passages:
        write_case(c)
    for c in passages:
        with open(os.path.join(OUT, f"{c['num']:03d}.toml"), "rb") as f:
            tomllib.load(f)
    print(f"Wrote {len(passages)} passages.")
    for n in (1, 2, len(passages)):
        c = passages[n - 1]
        print(f"\n--- passage {n} [{c['title_zh']}] ---")
        print(f"case ({len(c['case'])}): {c['case'][:54]}")


if __name__ == "__main__":
    main()
