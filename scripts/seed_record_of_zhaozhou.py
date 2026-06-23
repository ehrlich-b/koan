#!/usr/bin/env python3
"""Seed data/record-of-zhaozhou/NNN.toml from the CBETA TEI of 古尊宿語錄 (X1315).

Zhaozhou's record (趙州真際禪師語錄并行狀) is one self-contained work inside the
48-fascicle anthology 古尊宿語錄. It occupies fascicles 13-14: the level-1 div
趙州真際禪師語錄并行狀卷上, plus the sibling 之餘 (卷中/卷下) divs that follow,
up to the next master's record (雲門匡真禪師廣錄). We isolate exactly that span
of top-level <div>s and segment it:

  行狀        — Zhaozhou's life-record (the opening biographical paragraph).
  上堂 / 示眾  — his Dharma-hall discourses and instructions, one per source
                paragraph; `rend="inline"` continuations fold back in.
  十二時歌      — his "Song of the Twelve Hours" (kept whole, its twelve verses
                joined).
  頌          — his occasional verses (each titled by its source head).

The encomium and elegies that close the work (附趙王與師作真贊, 哭趙州和尚二首)
are by other hands, not Zhaozhou's sayings, and are left out — as are the
editorial colophons. CBETA apparatus is stripped by cbeta.py.

Merge-safe: refreshes only the original (zh) fields and the source title.
"""
import os
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbeta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources", "record-of-zhaozhou.x68n1315.tei.xml")
OUT = os.path.join(ROOT, "data", "record-of-zhaozhou")

START_SIG = "趙州真際禪師語錄"      # first work-level div of Zhaozhou's record
END_SIG = "雲門匡真禪師廣錄"        # the next master's record — stop before it

# Section heads that introduce a self-contained verse passage.
VERSE_HEADS = {"十二時歌", "見起塔乃有頌", "因見諸方見解異途乃有頌",
               "因魚鼓有頌", "因蓮花有頌"}
# Heads introducing material by other hands (appended praise / mourning) — drop.
DROP_HEADS = {"附趙王與師作真贊", "哭趙州和尚二首"}
# Editorial colophon and the running "之餘" section title that survive as <p>.
SKIP_P = ("廬山棲賢寶覺禪院", "趙州真際禪師語錄之餘", "趙州真際禪師語錄并行狀")


def basic(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lit(s):
    assert "'''" not in s, "content contains triple-quote"
    return "'''\n" + s + "\n'''" if s else "'''\n'''"


def title_for_body(text):
    if "示眾" in text[:8]:
        return "示眾"
    if "上堂" in text[:8]:
        return "上堂"
    return ""


def zhaozhou_blocks():
    """Return the block sequence for only Zhaozhou's run of top-level divs."""
    root, body, gaiji = cbeta.parse(SRC)
    TEI = cbeta.TEI

    def sig(el):
        h = el.find("." + "//" + TEI + "head")
        if h is not None:
            return cbeta.collapse("".join(h.itertext()))
        p = el.find("." + "//" + TEI + "p")
        return cbeta.collapse("".join(p.itertext())) if p is not None else ""

    divs = [c for c in list(body) if c.tag.endswith("}div")]
    start = end = None
    for i, c in enumerate(divs):
        s = sig(c)
        if start is None and START_SIG in s:
            start = i
        elif start is not None and END_SIG in s:
            end = i
            break
    assert start is not None and end is not None, "could not bound Zhaozhou span"
    out = []
    for c in divs[start:end]:
        out += cbeta.blocks(c, gaiji)
    return out


def segment():
    bl = zhaozhou_blocks()
    passages = []
    cur_verse_title = None     # set while collecting a multi-line verse head
    drop = False               # inside an other-hands appendix?

    for kind, rend, text in bl:
        if kind == "head":
            if text in DROP_HEADS:
                drop = True
                cur_verse_title = None
                continue
            drop = False
            if text in VERSE_HEADS:
                cur_verse_title = text
                passages.append({"title_zh": text, "case": ""})
            else:
                cur_verse_title = None
            continue
        if drop or not text.strip():
            continue
        if text.startswith(SKIP_P):
            continue

        if cur_verse_title is not None:
            # Accumulate verse lines under the current verse head.
            cur = passages[-1]
            cur["case"] = (cur["case"] + "\n" + text).strip() if cur["case"] else text
            continue

        # Prose discourse body.
        if rend == "inline" and passages and passages[-1]["title_zh"] not in VERSE_HEADS:
            passages[-1]["case"] += "\n" + text
        else:
            # The very first prose block is Zhaozhou's life-record.
            title = "行狀" if not passages else title_for_body(text)
            passages.append({"title_zh": title, "case": text})

    for i, p in enumerate(passages, 1):
        p["num"] = i
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
    by_title = {}
    for c in passages:
        by_title[c["title_zh"] or "(問)"] = by_title.get(c["title_zh"] or "(問)", 0) + 1
    print(f"Wrote {len(passages)} passages. By label: {by_title}")
    for n in (1, 2, len(passages)):
        c = passages[n - 1]
        print(f"\n--- passage {n} [{c['title_zh']}] ---")
        print(f"case ({len(c['case'])}): {c['case'][:54].replace(chr(10), '/')}")


if __name__ == "__main__":
    main()
