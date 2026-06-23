#!/usr/bin/env python3
"""Merge translation fragments from /tmp/koan-trans into data/<slug>/NNN.toml.

Each fragment is named `<slug>__<NNN>.toml` and holds any of these TOML literal
fields produced by a translator agent:
    title_en, intro_en, case_en, commentary_en, verse_en, pointer

We load the target data file, overlay the non-empty fragment fields (only onto
sections that actually exist in the target), and rewrite the file — preserving
the original zh text and the file's field shape. Idempotent; only touches files
that have a fragment.
"""
import glob
import os
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAG = sys.argv[1] if len(sys.argv) > 1 else "/tmp/koan-trans"
SECTIONS = ("intro", "case", "commentary", "verse")


def basic(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lit(s):
    s = s.strip("\n")
    assert "'''" not in s, "content contains triple-quote"
    return "'''\n" + s + "\n'''" if s else "'''\n'''"


def write_data(path, d):
    out = [
        f"number = {d['number']}",
        f"slug = {basic(d.get('slug', ''))}",
        f"title_zh = {basic(d.get('title_zh', ''))}",
        f"title_en = {basic(d.get('title_en', ''))}",
    ]
    if "title_pinyin" in d:
        out.append(f"title_pinyin = {basic(d.get('title_pinyin', ''))}")
    out.append("")
    for sec in SECTIONS:
        if f"{sec}_zh" in d:
            out += [f"{sec}_zh = {lit(d[f'{sec}_zh'])}",
                    f"{sec}_en = {lit(d.get(f'{sec}_en', ''))}", ""]
    out += [f"pointer = {lit(d.get('pointer', ''))}", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def main():
    applied = skipped = 0
    bad = []
    for fp in sorted(glob.glob(os.path.join(FRAG, "*.toml"))):
        name = os.path.basename(fp)[:-5]
        if "__" not in name:
            continue
        slug, num = name.rsplit("__", 1)
        target = os.path.join(ROOT, "data", slug, f"{num}.toml")
        if not os.path.exists(target):
            bad.append((name, "no target file"))
            continue
        try:
            frag = tomllib.load(open(fp, "rb"))
        except Exception as e:
            bad.append((name, f"unparseable: {e}"))
            continue
        d = tomllib.load(open(target, "rb"))
        changed = False
        for k in ("title_en", "intro_en", "case_en", "commentary_en", "verse_en", "pointer"):
            v = frag.get(k, "")
            if not (isinstance(v, str) and v.strip()):
                continue
            if k.endswith("_en") and k != "title_en":
                sec = k[:-3]
                if f"{sec}_zh" not in d:        # don't inject a section the source lacks
                    continue
            d[k] = v.strip("\n")
            changed = True
        if changed:
            write_data(target, d)
            applied += 1
        else:
            skipped += 1
    print(f"applied {applied}, skipped {skipped}, bad {len(bad)}")
    for n, why in bad[:25]:
        print("  BAD", n, why)


if __name__ == "__main__":
    main()
