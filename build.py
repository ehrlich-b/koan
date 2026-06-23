#!/usr/bin/env python3
"""Build the static site from data/*.toml into dist/.

Zero dependencies (Python 3.11+ stdlib). Reads each collection's
collection.toml plus its numbered case files and emits plain HTML/CSS/JS:

    dist/index.html                     home + search
    dist/about.html                     project / license
    dist/<collection>/index.html        collection intro + case list
    dist/<collection>/NN-slug.html      one page per case (original + translation + pointer)
    dist/search-index.json              client-side search index
    dist/style.css, dist/search.js      copied from assets/

Deployed at the domain root (koan.ehrlich.dev), so all links are root-relative.
"""
import html
import json
import os
import re
import shutil
import tomllib

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
DIST = os.path.join(ROOT, "dist")
ASSETS = os.path.join(ROOT, "assets")

SITE_BRAND = "公案 · kōan"
SITE_DESC = "A public-domain repository of Zen kōan in the original Chinese with free English translations."


def esc(s):
    return html.escape(s, quote=True)


def load_collection(slug):
    cdir = os.path.join(DATA, slug)
    with open(os.path.join(cdir, "collection.toml"), "rb") as f:
        meta = tomllib.load(f)
    cases = []
    for name in sorted(os.listdir(cdir)):
        if re.fullmatch(r"\d+\.toml", name):
            with open(os.path.join(cdir, name), "rb") as f:
                cases.append(tomllib.load(f))
    cases.sort(key=lambda c: c["number"])
    meta["_pad"] = 3 if cases and max(c["number"] for c in cases) >= 100 else 2
    return meta, cases


def render_prose(s):
    s = s.strip()
    if not s:
        return ""
    paras = re.split(r"\n\s*\n", s)
    return "\n".join(
        "<p>" + esc(p.strip()).replace("\n", "<br>\n") + "</p>" for p in paras if p.strip()
    )


def render_verse(s):
    lines = [l for l in s.strip().split("\n") if l.strip()]
    return "".join('<span class="line">' + esc(l) + "</span>\n" for l in lines)


def bilingual(zh, en, kind="prose"):
    render = render_verse if kind == "verse" else render_prose
    zh_html = render(zh)
    if en.strip():
        en_html = render(en)
    else:
        en_html = '<p class="untranslated">English translation not yet available — contributions welcome.</p>'
    return (
        '<div class="pair">\n'
        f'<div class="zh" lang="zh-Hant">{zh_html}</div>\n'
        f'<div class="en">{en_html}</div>\n'
        "</div>"
    )


def page(title, body, description, *, active=""):
    nav = [("/", "Home", ""), ("/about.html", "About", "about")]
    links = "".join(
        f'<a href="{href}"{" aria-current=page" if key and key == active else ""}>{esc(label)}</a>'
        for href, label, key in nav
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header class="site-head"><div class="wrap">
<span class="brand"><a href="/">{SITE_BRAND}</a></span>
<nav>{links}</nav>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer class="site-foot"><div class="wrap">
<p>Original texts are in the public domain. English translations and pointers are released under <a href="/about.html">CC0 1.0</a> — no rights reserved.</p>
<p>{esc(SITE_DESC)}</p>
</div></footer>
<script src="/search.js" defer></script>
</body>
</html>
"""


def koan_filename(c, pad=2):
    base = f"{c['number']:0{pad}d}"
    return f"{base}-{c['slug']}.html" if c.get("slug") else f"{base}.html"


def koan_url(meta, c):
    return f"/{meta['slug']}/{koan_filename(c, meta.get('_pad', 2))}"


SECTION_DEFAULTS = {"intro": "Introduction", "commentary": "Commentary", "verse": "Verse"}


def title_of(c):
    return c.get("title_en") or c.get("title_zh") or f"Case {c['number']}"


def titles(c):
    """(main title, secondary Chinese title). Avoids showing the Chinese twice
    when there is no English title yet."""
    en = (c.get("title_en") or "").strip()
    zh = (c.get("title_zh") or "").strip()
    if en:
        return en, zh
    if zh:
        return zh, ""
    return f"Case {c['number']}", ""


def heading(en, zh):
    z = f' <span class="zh" lang="zh-Hant">{esc(zh)}</span>' if zh else ""
    return f"<h2>{esc(en)}{z}</h2>"


def section_label(meta, sec):
    return (meta.get(f"label_{sec}_en") or SECTION_DEFAULTS[sec],
            meta.get(f"label_{sec}_zh", ""))


def build_koan_page(meta, cases, i):
    c = cases[i]
    slug = meta["slug"]
    n = c["number"]
    main_title, zh_title = titles(c)
    pinyin = c.get("title_pinyin", "").strip()

    parts = [
        '<nav class="koannav">',
        (f'<a href="{koan_url(meta, cases[i-1])}">← {esc(title_of(cases[i-1]))}</a>'
         if i > 0 else f'<a href="/{slug}/">{esc(meta["title_en"])}</a>'),
        f'<a class="spacer" href="/{slug}/">all {len(cases)} cases</a>',
        (f'<a href="{koan_url(meta, cases[i+1])}">{esc(title_of(cases[i+1]))} →</a>'
         if i < len(cases) - 1 else f'<a href="/{slug}/">{esc(meta["title_en"])}</a>'),
        "</nav>",
        f'<h1><span class="n">{n}</span>{esc(main_title)}'
        + (f'<span class="zh-title" lang="zh-Hant">{esc(zh_title)}</span>' if zh_title else "")
        + "</h1>",
    ]
    if pinyin:
        parts.append(f'<p class="pinyin">{esc(pinyin)}</p>')

    # Introduction (垂示 / 示眾), when the collection has one, precedes the case.
    if c.get("intro_zh", "").strip():
        en, zh = section_label(meta, "intro")
        parts += [f'<section class="intro">', heading(en, zh),
                  bilingual(c["intro_zh"], c.get("intro_en", "")), "</section>"]

    parts += ['<section class="case">',
              bilingual(c["case_zh"], c.get("case_en", "")), "</section>"]

    for sec, kind in (("commentary", "prose"), ("verse", "verse")):
        if c.get(f"{sec}_zh", "").strip():
            en, zh = section_label(meta, sec)
            parts += [f'<section class="{sec}">', heading(en, zh),
                      bilingual(c[f"{sec}_zh"], c.get(f"{sec}_en", ""), kind=kind),
                      "</section>"]

    if c.get("pointer", "").strip():
        parts += ['<aside class="pointer">', "<h2>Pointer</h2>",
                  render_prose(c["pointer"]), "</aside>"]

    parts.append('<nav class="koannav">')
    if i > 0:
        parts.append(f'<a href="{koan_url(meta, cases[i-1])}">← previous</a>')
    parts.append(f'<a class="spacer" href="/{slug}/">contents</a>')
    if i < len(cases) - 1:
        parts.append(f'<a href="{koan_url(meta, cases[i+1])}">next →</a>')
    parts.append("</nav>")

    desc = (c.get("case_en") or c["case_zh"]).strip().replace("\n", " ")[:155]
    return page(f'{meta["title_en"]} {n}. {main_title}', "\n".join(parts), desc, active=slug)


def build_collection_page(meta, cases):
    slug = meta["slug"]
    head = [
        f'<h1>{esc(meta["title_en"])}<span class="zh-title" lang="zh-Hant">{esc(meta["title_zh"])}</span></h1>',
        f'<p class="pinyin">{esc(meta.get("title_pinyin",""))} · {esc(meta.get("title_ja",""))} · compiled by {esc(meta["compiler"])}, {esc(meta["date"])} ({esc(meta.get("dynasty",""))})</p>',
        f'<div class="lede">{render_prose(meta.get("intro_en",""))}</div>',
    ]
    if meta.get("preface_zh", "").strip():
        head.append(heading(meta.get("label_preface_en") or "Preface", meta.get("label_preface_zh", "序")))
        head.append(bilingual(meta["preface_zh"], meta.get("preface_en", "")))
    if meta.get("opening_verse_zh", "").strip():
        head.append(heading(meta.get("label_opening_en") or "Opening Verse", meta.get("label_opening_zh", "頌")))
        head.append(bilingual(meta["opening_verse_zh"], meta.get("opening_verse_en", ""), kind="verse"))

    head.append('<div class="search"><input id="search" type="search" placeholder="Search the cases…" data-index="/search-index.json" autocomplete="off"></div>')
    head.append('<ul id="search-results"></ul>')

    head.append(f"<h2>The {len(cases)} Cases</h2>")
    items = ['<ul class="koan-list">']
    for c in cases:
        todo = "" if c.get("case_en", "").strip() else '<span class="todo">original only</span>'
        mt, zt = titles(c)
        zspan = f'<span class="zh" lang="zh-Hant">{esc(zt)}</span>' if zt else ""
        items.append(
            f'<li><a href="{koan_url(meta, c)}">'
            f'<span class="n">{c["number"]}</span>'
            f'<span class="t">{esc(mt)}</span>{todo}{zspan}</a></li>'
        )
    items.append("</ul>")
    head.append("\n".join(items))

    desc = f'{meta["title_en"]} ({meta.get("title_ja","")}): all {len(cases)} kōan in the original Chinese with free English translations.'
    return page(meta["title_en"], "\n".join(head), desc, active=slug)


def _featured(collections):
    for meta, cases in collections:
        for c in cases:
            if c.get("case_en", "").strip() and c.get("pointer", "").strip():
                return meta, c
    return None, None


def build_home(collections):
    body = [
        f"<h1>{SITE_BRAND}</h1>",
        '<div class="lede">',
        '<p>Kōan (<span class="zh" lang="zh-Hant">公案</span>) is a legal term. It means "public case" - a case on the record, the way a court keeps precedents. Zen borrowed the word for these: short, odd exchanges between a teacher and a student, collected and studied like case law. Most of them don\'t make sense, and a lot of them are funny, but they\'re supposed to be: a kōan is built to jam the part of your head that goes looking for the answer.</p>',
        '<p>Each entry has three parts: the original, a translation, and a pointer. The pointer is the useful bit. It won\'t solve anything, but it gives you what you\'d need to get the joke: who these people are, and where the trap is set. The originals are public domain; the translations are free to use.</p>',
        "</div>",
    ]

    fmeta, fc = _featured(collections)
    if fc:
        url = koan_url(fmeta, fc)
        body += [
            '<section class="featured">',
            "<h2>How it works</h2>",
            '<p>A taste — the most famous case in the book:</p>',
            f'<h3 class="featured-title"><span class="n">{fc["number"]}</span>{esc(fc.get("title_en") or fc["title_zh"])}'
            f'<span class="zh-title" lang="zh-Hant">{esc(fc["title_zh"])}</span></h3>',
            bilingual(fc["case_zh"], fc.get("case_en", "")),
            '<aside class="pointer"><h2>Pointer</h2>',
            render_prose(fc["pointer"]),
            "</aside>",
            f'<p class="more"><a href="{url}">Read Wumen\'s full commentary and verse on this case →</a></p>',
            "</section>",
        ]

    body += [
        '<div class="search"><input id="search" type="search" placeholder="Search all cases…" data-index="/search-index.json" autocomplete="off"></div>',
        '<ul id="search-results"></ul>',
        "<h2>Collections</h2>",
        '<ul class="collections">',
    ]
    for meta, cases in collections:
        n_tr = sum(1 for c in cases if c.get("case_en", "").strip())
        body.append(
            f'<li><h3><a href="/{meta["slug"]}/">{esc(meta["title_en"])} '
            f'<span class="zh" lang="zh-Hant">{esc(meta["title_zh"])}</span></a></h3>'
            f'<p class="meta">{esc(meta["compiler"])} · {esc(meta["date"])} · '
            f'{len(cases)} cases · {n_tr} translated so far</p></li>'
        )
    body.append("</ul>")
    return page(SITE_BRAND, "\n".join(body), SITE_DESC)


def build_about(collections):
    body = ["<h1>About</h1>", '<div class="lede">']
    body.append(render_prose(
        f"{SITE_DESC}\n\n"
        "Zen kōan come down to us mostly in Classical Chinese, in collections composed eight or nine centuries ago. "
        "Those original texts are unambiguously in the public domain. Most good English translations, however, are still under copyright. "
        "This project pairs the public-domain originals with new translations that are themselves freely usable — so the whole thing, original and translation alike, belongs to everyone."
    ))
    body.append("</div>")
    body.append("<h2>The three parts of each entry</h2>")
    body.append(render_prose(
        "Original — the public-domain classical Chinese text, set in our own punctuation. The wording is the ancient text itself, checked character by character, not any modern edition.\n\n"
        "Translation — faithful but readable: accurate to the Chinese, in natural modern English, with a light touch of bracketed glossing only where a term truly needs it.\n\n"
        "Pointer — a curator's note. Not an interpretation that resolves the kōan (that would defeat its purpose) but an oblique nudge: the cultural and doctrinal context a monk in the original audience already carried, and which a modern reader usually lacks."
    ))
    body.append("<h2>Sources & license</h2>")
    items = []
    for m, _ in collections:
        note = esc(m.get("source_note", ""))
        if not note:
            continue
        link = f' (<a href="{esc(m["source_url"])}">source</a>)' if m.get("source_url") else ""
        items.append(f'<li>{esc(m["title_en"])} — {note}{link}</li>')
    body.append(f"<ul>{''.join(items)}</ul>")
    body.append(render_prose(
        "Original texts: public domain. Translations and pointers: dedicated to the public domain under the Creative Commons CC0 1.0 Universal dedication — you may copy, adapt, and redistribute them for any purpose, no permission or attribution required."
    ))
    return page("About", "\n".join(body), "About this project, its method, sources, and license.", active="about")


def build_search_index(collections):
    out = []
    for meta, cases in collections:
        cshort = meta["title_en"].replace("The ", "")
        for c in cases:
            if not c.get("case_en", "").strip():
                continue
            body = " ".join(
                c.get(k, "") for k in ("intro_en", "case_en", "commentary_en", "verse_en", "pointer", "case_zh")
            )
            body = re.sub(r"\s+", " ", body).strip()
            mt, zt = titles(c)
            out.append({
                "u": koan_url(meta, c),
                "c": cshort,
                "n": c["number"],
                "te": mt,
                "tz": zt,
                "b": body,
            })
    return out


def main():
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(DIST)

    collections = []
    for slug in sorted(os.listdir(DATA)):
        if os.path.exists(os.path.join(DATA, slug, "collection.toml")):
            collections.append(load_collection(slug))
    # Display order: the famous koan books first, then recorded-sayings.
    # Unknown collections sort after these, alphabetically.
    order = ["gateless-gate", "blue-cliff-record", "book-of-serenity",
             "record-of-linji", "record-of-zhaozhou", "record-of-layman-pang"]
    collections.sort(key=lambda mc: (order.index(mc[0]["slug"]) if mc[0]["slug"] in order else len(order), mc[0]["slug"]))

    n_pages = 0
    for meta, cases in collections:
        cdir = os.path.join(DIST, meta["slug"])
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(build_collection_page(meta, cases))
        for i in range(len(cases)):
            with open(os.path.join(cdir, koan_filename(cases[i], meta["_pad"])), "w", encoding="utf-8") as f:
                f.write(build_koan_page(meta, cases, i))
            n_pages += 1

    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_home(collections))
    with open(os.path.join(DIST, "about.html"), "w", encoding="utf-8") as f:
        f.write(build_about(collections))
    with open(os.path.join(DIST, "search-index.json"), "w", encoding="utf-8") as f:
        json.dump(build_search_index(collections), f, ensure_ascii=False, separators=(",", ":"))

    for asset in ("style.css", "search.js"):
        shutil.copy(os.path.join(ASSETS, asset), os.path.join(DIST, asset))

    n_tr = sum(1 for _, cases in collections for c in cases if c.get("case_en", "").strip())
    n_total = sum(len(cases) for _, cases in collections)
    print(f"Built {len(collections)} collection(s): {n_pages} case pages, "
          f"{n_tr}/{n_total} translated. Output in {DIST}/")


if __name__ == "__main__":
    main()
