#!/usr/bin/env python3
"""Seed data/record-of-linji/NNN.toml from the archived CBETA TEI.

The Record of Linji (臨濟錄, T1985) is recorded sayings, not numbered kōan, so
we segment it into sequential passages along its own editorial divisions:

  上堂 / 示眾  — the master's Dharma-hall discourses and instructions (the main
                語錄 body), one passage per source paragraph; the source's
                `rend="inline"` continuation paragraphs are folded back into the
                discourse they continue.
  勘辨        — Critical Examinations (encounter dialogues), one per paragraph.
  行錄        — Record of Activities / pilgrimage, one per paragraph.

The three prefaces are front matter, not sayings; the standard preface (Ma
Fang's 鎮州臨濟慧照禪師語錄序) is kept on the collection page, the two later
descendants' prefaces and the printers' colophons are dropped. CBETA apparatus
(notes, variant readings, capping phrases) is stripped by cbeta.py.

Merge-safe: refreshes only the original (zh) fields and the source title; never
touches translations, pointers, or a hand-written slug.
"""
import os
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbeta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources", "record-of-linji.t47n1985.tei.xml")
OUT = os.path.join(ROOT, "data", "record-of-linji")

# Section heads in document order. Everything before the first one is the main
# discourse body (上堂 / 示眾); 勘辨 and 行錄 follow.
SECTION_HEADS = {"勘辨", "行錄"}

# Colophons / attributions that survive as <p> at the tail but are not content.
SKIP_PREFIX = ("住大名府興化", "永享")


def title_for_body(text):
    """Label a main-body passage by its opening editorial marker."""
    if "示眾" in text[:10]:
        return "示眾"
    # A Dharma-hall discourse opens with 上堂, or with the master being invited
    # to take the seat (請師升座 … 上堂).
    if "上堂" in text[:18] or "升座" in text[:18]:
        return "上堂"
    return ""  # an embedded 問答 exchange — no section label


def basic(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lit(s):
    assert "'''" not in s, "content contains triple-quote"
    return "'''\n" + s + "\n'''" if s else "'''\n'''"


def segment():
    _, body, gaiji = cbeta.parse(SRC)
    bl = cbeta.blocks(body, gaiji)

    passages = []          # list of {"title_zh", "case"}
    section = None          # None until first head; then "勘辨" / "行錄"
    seen_body = False       # have we passed the prefaces into the body yet?

    for kind, rend, text in bl:
        if not text.strip():
            continue
        if kind == "head":
            if text in SECTION_HEADS:
                section = text
                seen_body = True
            continue
        # Prefaces precede the first real talk; the body opens at the first
        # paragraph mentioning 上堂 (the inaugural Dharma-hall discourse).
        if section is None and not seen_body:
            if "上堂" in text or "升座" in text:
                seen_body = True
            else:
                continue  # still in the prefaces
        if text.startswith(SKIP_PREFIX):
            continue

        if section in SECTION_HEADS:
            passages.append({"title_zh": section, "case": text})
            continue

        # Main discourse body.
        if rend == "inline" and passages:
            # Continuation of the master's preceding discourse.
            passages[-1]["case"] += "\n" + text
        else:
            passages.append({"title_zh": title_for_body(text), "case": text})

    for i, p in enumerate(passages, 1):
        p["num"] = i
    return passages


def preface():
    """Ma Fang's preface (鎮州臨濟慧照禪師語錄序) for the collection page."""
    _, body, gaiji = cbeta.parse(SRC)
    bl = cbeta.blocks(body, gaiji)
    want = False
    for kind, rend, text in bl:
        if kind == "head" and text == "鎮州臨濟慧照禪師語錄序":
            want = True
            continue
        if want and kind == "p" and text.strip():
            return text
    return ""


def write_case(c):
    path = os.path.join(OUT, f"{c['num']:03d}.toml")
    old = {}
    if os.path.exists(path):
        with open(path, "rb") as f:
            old = tomllib.load(f)
    g = lambda k, d="": old.get(k, d)
    # title_zh comes from the source section; a hand-edited title_zh, if any,
    # wins so curators can rename a passage.
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

    by_title = {}
    for c in passages:
        by_title[c["title_zh"] or "(問)"] = by_title.get(c["title_zh"] or "(問)", 0) + 1
    print(f"Wrote {len(passages)} passages. By label: {by_title}")
    print(f"Preface length: {len(preface())} chars")
    for n in (1, len(passages)):
        c = passages[n - 1]
        print(f"\n--- passage {n} [{c['title_zh']}] ---")
        print(f"case ({len(c['case'])}): {c['case'][:54]}")


if __name__ == "__main__":
    main()
