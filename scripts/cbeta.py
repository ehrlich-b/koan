"""Shared helpers for turning CBETA TEI (P5) into clean plain text.

CBETA distributes the Taishō canon as TEI XML. For our purposes we want the
running text of the body with the scholarly apparatus removed:

  - <note> (footnotes AND the interlinear "capping phrases" 著語) -> dropped
  - <app><lem>/<rdg>  -> keep the lemma, drop variant readings
  - <choice><corr>/<sic>, <reg>/<orig> -> keep the corrected/regularized form
  - <g ref="#CBxxxx"/> (gaiji)  -> resolved via the header's <charDecl>
  - <lb/> <pb/> <milestone/> <anchor/>  -> dropped (source layout, not content)

Verses live in <lg>/<l>; everything else is <p>. `blocks()` returns those two
kinds in document order so a caller can segment by content.
"""
import re
import xml.etree.ElementTree as ET

TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

_DROP = {"note", "pb", "lb", "milestone", "anchor", "figure", "graphic",
         "byline", "docNumber"}


def _tag(el):
    return el.tag.split("}", 1)[1] if "}" in el.tag else el.tag


def load_gaiji(root):
    """Map CBETA gaiji ids (e.g. 'CB01234') to a best-effort Unicode char."""
    out = {}
    for char in root.iter(TEI + "char"):
        cid = char.get(XML_ID)
        if not cid:
            continue
        pick = None
        for mp in char.findall(TEI + "mapping"):
            t = mp.get("type")
            if t == "unicode" and mp.text:
                pick = mp.text
                break
            if t in ("normal_unicode", "Romanized") and mp.text and not pick:
                pick = mp.text
        if pick:
            out[cid] = _resolve(pick)
    return out


def _resolve(text):
    text = text.strip()
    m = re.fullmatch(r"(?:U\+|0x)?([0-9A-Fa-f]{4,6})", text)
    if m:
        try:
            return chr(int(m.group(1), 16))
        except ValueError:
            return "□"
    return text if len(text) == 1 else "□"


def _emit(el, gaiji, out, tail):
    """Append the textual content of `el` to list `out` (tail = include el.tail)."""
    tag = _tag(el)
    if tag in _DROP:
        if tail and el.tail:
            out.append(el.tail)
        return
    if tag == "g":
        out.append(gaiji.get(el.get("ref", "").lstrip("#"), "□"))
        if tail and el.tail:
            out.append(el.tail)
        return
    if tag == "app":
        lem = el.find(TEI + "lem")
        if lem is not None:
            _emit(lem, gaiji, out, tail=False)
        if tail and el.tail:
            out.append(el.tail)
        return
    if tag == "choice":
        pick = el.find(TEI + "corr")
        if pick is None:
            pick = el.find(TEI + "reg")
        if pick is None:
            kids = list(el)
            pick = kids[0] if kids else None
        if pick is not None:
            _emit(pick, gaiji, out, tail=False)
        if tail and el.tail:
            out.append(el.tail)
        return
    # default: own text, then children (with their tails), then own tail
    if el.text:
        out.append(el.text)
    for child in el:
        _emit(child, gaiji, out, tail=True)
    if tail and el.tail:
        out.append(el.tail)


def text_of(el, gaiji):
    """Clean inline text of an element (its tail excluded)."""
    out = []
    _emit(el, gaiji, out, tail=False)
    return "".join(out)


def collapse(s):
    """Classical Chinese uses no spaces; drop all whitespace runs."""
    return re.sub(r"\s+", "", s)


_DIG = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9}
_UNIT = {"十": 10, "百": 100, "千": 1000}


def cjk_num(s):
    """Parse a Chinese numeral, handling both positional digits (一〇〇 = 100,
    as the Blue Cliff Record numbers its cases) and standard form (二十一 = 21,
    一百 = 100, as the Book of Serenity does)."""
    if s and all(c in _DIG for c in s):
        return int("".join(str(_DIG[c]) for c in s))
    total, num = 0, 0
    for c in s:
        if c in _DIG:
            num = _DIG[c]
        elif c in _UNIT:
            total += (num or 1) * _UNIT[c]
            num = 0
    return total + num


def parse(path):
    root = ET.parse(path).getroot()
    gaiji = load_gaiji(root)
    body = root.find(f"{TEI}text/{TEI}body")
    return root, body, gaiji


def blocks(body, gaiji):
    """Yield (kind, rend, text) for each <p> and <lg> in document order.

    <p> text is whitespace-collapsed prose; <lg> text is its <l> lines joined
    by newlines. Containers (cb:div, etc.) are descended into; layout/apparatus
    elements are skipped.
    """
    res = []

    def walk(el):
        for child in el:
            t = _tag(child)
            if t == "p":
                res.append(("p", child.get("rend", ""), collapse(text_of(child, gaiji))))
            elif t == "head":
                res.append(("head", child.get("rend", ""), collapse(text_of(child, gaiji))))
            elif t == "lg":
                lines = [collapse(text_of(l, gaiji)) for l in child.iter(TEI + "l")]
                res.append(("lg", child.get("rend", ""), "\n".join(x for x in lines if x)))
            elif t in _DROP:
                continue
            else:
                walk(child)

    walk(body)
    return res
