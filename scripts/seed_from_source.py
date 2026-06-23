#!/usr/bin/env python3
"""Seed per-koan data files from the archived original source.

Parses sources/gateless-gate.zh.wikitext (Chinese Wikisource, public domain)
into data/gateless-gate/NN.toml, one file per case, with the original Chinese
populated and the English / pointer fields left blank for human translation.

Re-running is safe: existing English translations and pointers are preserved;
only the original (zh) text and title metadata are refreshed from source.

This is a one-shot bootstrap / refresh tool, not part of the normal build.
"""
import os
import re
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources", "gateless-gate.zh.wikitext")
OUT = os.path.join(ROOT, "data", "gateless-gate")
FW = "　"  # full-width (ideographic) space

# Curated English titles + URL slugs for the 48 cases. The Chinese titles are
# read from the source headers; these are the translator's renderings.
TITLES = {
    1:  ("Zhaozhou's Dog", "zhaozhous-dog"),
    2:  ("Baizhang's Fox", "baizhangs-fox"),
    3:  ("Juzhi Raises a Finger", "juzhi-raises-a-finger"),
    4:  ("The Barbarian Has No Beard", "barbarian-has-no-beard"),
    5:  ("Xiangyan Up a Tree", "xiangyan-up-a-tree"),
    6:  ("The World-Honored One Holds Up a Flower", "buddha-holds-up-a-flower"),
    7:  ("Zhaozhou: Wash Your Bowl", "zhaozhou-wash-your-bowl"),
    8:  ("Xizhong Makes a Cart", "xizhong-makes-a-cart"),
    9:  ("The Buddha of Supreme Penetration", "great-universal-wisdom"),
    10: ("Qingshui, Alone and Poor", "qingshui-alone-and-poor"),
    11: ("Zhaozhou Examines the Hermits", "zhaozhou-examines-the-hermits"),
    12: ("Ruiyan Calls 'Master'", "ruiyan-calls-master"),
    13: ("Deshan Carries His Bowl", "deshan-carries-his-bowl"),
    14: ("Nanquan Cuts the Cat", "nanquan-cuts-the-cat"),
    15: ("Dongshan's Sixty Blows", "dongshan-sixty-blows"),
    16: ("The Bell and the Seven-Panel Robe", "bell-and-seven-panel-robe"),
    17: ("The National Teacher's Three Calls", "national-teachers-three-calls"),
    18: ("Dongshan's Three Pounds of Flax", "dongshan-three-pounds-of-flax"),
    19: ("Ordinary Mind Is the Way", "ordinary-mind-is-the-way"),
    20: ("A Person of Great Strength", "person-of-great-strength"),
    21: ("Yunmen's Dried Shit-Stick", "yunmen-dried-shit-stick"),
    22: ("Mahakashyapa's Flagpole", "mahakashyapa-flagpole"),
    23: ("Think Neither Good Nor Evil", "think-neither-good-nor-evil"),
    24: ("Leaving Speech Behind", "leaving-speech-behind"),
    25: ("Preaching from the Third Seat", "preaching-from-the-third-seat"),
    26: ("Two Monks Roll Up the Blind", "two-monks-roll-the-blind"),
    27: ("Not Mind, Not Buddha", "not-mind-not-buddha"),
    28: ("Long Have I Heard of Longtan", "long-heard-of-longtan"),
    29: ("Not the Wind, Not the Flag", "not-the-wind-not-the-flag"),
    30: ("This Very Mind Is Buddha", "this-mind-is-buddha"),
    31: ("Zhaozhou Examines the Old Woman", "zhaozhou-examines-the-old-woman"),
    32: ("A Non-Buddhist Questions the Buddha", "non-buddhist-questions-buddha"),
    33: ("Neither Mind Nor Buddha", "neither-mind-nor-buddha"),
    34: ("Knowing Is Not the Way", "knowing-is-not-the-way"),
    35: ("Qiannü and Her Soul", "qiannu-and-her-soul"),
    36: ("Meeting an Adept on the Road", "meeting-an-adept-on-the-road"),
    37: ("The Cypress in the Garden", "cypress-in-the-garden"),
    38: ("A Buffalo Passes the Window", "buffalo-passes-the-window"),
    39: ("Yunmen: Caught by Your Own Words", "yunmen-caught-by-words"),
    40: ("Kicking Over the Water Jug", "kicking-over-the-water-jug"),
    41: ("Bodhidharma Pacifies the Mind", "bodhidharma-pacifies-the-mind"),
    42: ("The Woman Comes Out of Samadhi", "woman-comes-out-of-samadhi"),
    43: ("Shoushan's Bamboo Staff", "shoushan-bamboo-staff"),
    44: ("Bajiao's Staff", "bajiao-staff"),
    45: ("Who Is He?", "who-is-he"),
    46: ("Step Forward from the Top of the Pole", "step-from-top-of-pole"),
    47: ("Doushuai's Three Barriers", "doushuai-three-barriers"),
    48: ("Qianfeng's One Road", "qianfeng-one-road"),
}

HDR = re.compile(r"^==(\d+)\.\s*(.+?)==\s*$")
COMMENT_MARK = "【無門曰】"
VERSE_MARK = "【頌曰】"

# Fields that hold human work and must never be clobbered on re-seed.
PRESERVE = ("title_en", "title_pinyin", "case_en", "commentary_en",
            "verse_en", "pointer")


def clean(line):
    return line.strip(FW + " \t")


def join_prose(lines):
    return "\n".join(clean(l) for l in lines if clean(l))


def join_verse(lines):
    out = []
    for l in lines:
        l = clean(l)
        if not l:
            continue
        out.extend(p for p in re.split(FW + "+", l) if p)
    return "\n".join(out)


def parse_cases(text):
    lines = text.splitlines()
    heads = [(i, int(m.group(1)), m.group(2).strip())
             for i, l in enumerate(lines) if (m := HDR.match(l))]
    # End of the numbered cases = first non-numbered "==" header after case 1.
    end = len(lines)
    for i, l in enumerate(lines):
        if i > heads[0][0] and l.startswith("==") and not HDR.match(l):
            end = i
            break
    bounds = [h[0] for h in heads] + [end]
    cases = []
    for k, (li, num, tzh) in enumerate(heads):
        block = lines[li + 1:bounds[k + 1]]
        # Drop the redundant "<numeral>　<title>" line that repeats the header.
        body = list(block)
        for j, l in enumerate(body):
            if clean(l):
                if clean(l).endswith(tzh):
                    body = body[j + 1:]
                break
        seg, case_l, com_l, verse_l = "case", [], [], []
        for l in body:
            s = clean(l)
            if s == COMMENT_MARK:
                seg = "com"; continue
            if s == VERSE_MARK:
                seg = "verse"; continue
            {"case": case_l, "com": com_l, "verse": verse_l}[seg].append(l)
        cases.append({
            "number": num, "title_zh": tzh,
            "case_zh": join_prose(case_l),
            "commentary_zh": join_prose(com_l),
            "verse_zh": join_verse(verse_l),
        })
    return cases


def basic(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def literal(s):
    # TOML multi-line literal string; preserves CJK and line breaks verbatim.
    assert "'''" not in s, "content contains triple-quote"
    return "'''\n" + s + "\n'''" if s else "'''\n'''"


def write_koan(c):
    path = os.path.join(OUT, f"{c['number']:02d}.toml")
    existing = {}
    if os.path.exists(path):
        with open(path, "rb") as f:
            existing = tomllib.load(f)
    title_en, slug = TITLES[c["number"]]
    fields = {
        "title_en": existing.get("title_en") or title_en,
        "title_pinyin": existing.get("title_pinyin", ""),
        "case_en": existing.get("case_en", ""),
        "commentary_en": existing.get("commentary_en", ""),
        "verse_en": existing.get("verse_en", ""),
        "pointer": existing.get("pointer", ""),
    }
    out = [
        f"number = {c['number']}",
        f"slug = {basic(slug)}",
        f"title_zh = {basic(c['title_zh'])}",
        f"title_en = {basic(fields['title_en'])}",
        f"title_pinyin = {basic(fields['title_pinyin'])}",
        "",
        f"case_zh = {literal(c['case_zh'])}",
        f"case_en = {literal(fields['case_en'])}",
        "",
        f"commentary_zh = {literal(c['commentary_zh'])}",
        f"commentary_en = {literal(fields['commentary_en'])}",
        "",
        f"verse_zh = {literal(c['verse_zh'])}",
        f"verse_en = {literal(fields['verse_en'])}",
        "",
        f"pointer = {literal(fields['pointer'])}",
        "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return path


def main():
    with open(SRC, encoding="utf-8") as f:
        cases = parse_cases(f.read())
    assert len(cases) == 48, f"expected 48 cases, got {len(cases)}"
    for c in cases:
        write_koan(c)
    # Validate everything round-trips through the TOML parser.
    for c in cases:
        p = os.path.join(OUT, f"{c['number']:02d}.toml")
        with open(p, "rb") as f:
            tomllib.load(f)
    print(f"Wrote/refreshed {len(cases)} koan files in {OUT}")
    sample = cases[0]
    print("\n--- sanity check: case 1 ---")
    print("title_zh:", sample["title_zh"])
    print("case_zh :", sample["case_zh"])
    print("verse_zh:\n" + sample["verse_zh"])


if __name__ == "__main__":
    main()
