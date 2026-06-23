# kōan — Project Instructions

**Site:** koan.ehrlich.dev

## What This Is

A public-domain repository of Zen kōan in the original Classical Chinese, paired
with free (CC0) English translations. The point is a genuinely free alternative
to the copyrighted translations: the originals are centuries old and public
domain, and our translations are dedicated to the public domain too.

## The Three Parts of Every Entry

Each case is presented as **Original → Translation → Pointer**:

1. **Original** — source text, transcribed from a public-domain edition, checked
   character by character. Never paraphrased, never "cleaned up."
2. **Translation** — faithful but readable (see below).
3. **Pointer** — the curator's note. This is the distinctive element. See voice
   rules below; getting these right is most of the value of the project.

Wumen's own commentary and verse are part of the original work and get
translated like everything else. The pointer is *separate* — our voice, not his.

## Pointer Voice (important)

A pointer gives a modern reader the foothold a monk in the original audience
already had. It does **not** explain the kōan.

- **Supply the missing context:** who the figures are, what a Buddhist term
  meant, the cultural reference or the wordplay, where the trap in the question
  is. That's what "the smol american mind" actually lacks.
- **Do not resolve it.** Never write "the meaning is X" or hand over an answer.
  Point at where the live question sits and leave it live. Often the best
  pointer ends by handing the question back.
- **Tone:** plain, wry, a little irreverent, humane, contemporary. Never
  reverent-mystical, never academic, no incense.
- **Length:** one short paragraph (2–5 sentences).
- Assume zero Zen background; never condescend.

## Translation Philosophy

Faithful but readable. Accurate to the Chinese, in natural modern English. Use
bracketed glosses `[like this]` sparingly, only where a term genuinely needs it.
Keep load-bearing technical terms (e.g. *Wú/Mu*) and let the pointer carry the
gloss. Flag genuinely uncertain renderings rather than papering over them.

## Data Model

Flat TOML, one file per case, `data/<collection>/NN.toml`:

```
number, slug, title_zh, title_en, title_pinyin
intro_zh / intro_en             (the introduction: 垂示 / 示眾, where present)
case_zh / case_en               (the case proper: 本則)
commentary_zh / commentary_en   (e.g. Wumen's comment 無門曰)
verse_zh / verse_en             (頌)
pointer                         (English only — our voice)
```

Not every collection uses every section — the Gateless Gate has a case +
commentary + verse; the Blue Cliff Record and Book of Serenity have an intro +
case + verse (no commentary in our core depth). `build.py` renders whichever
`*_zh` fields are non-empty. `slug` and `title_en` may be empty (numbered books
fall back to `Case N` and numeric URLs).

Multi-line text uses TOML literal strings (`'''…'''`) so CJK and line breaks are
verbatim. Verses are stored one phrase per line.

Collection-level metadata lives in `collection.toml`: titles, compiler, dates,
`source_url`/`source_note`, licenses, an `intro_en`, optional prefaces/opening
verse, and **section-label overrides** — `label_intro_zh`, `label_commentary_en`,
`label_commentary_zh`, `label_verse_zh`, etc. (defaults are Introduction /
Commentary / Verse with no Chinese tag).

Empty `*_en`/`pointer` is fine — the site renders the original with a
"not yet available" note, so originals can land before translations.

## Pipeline

Seeders parse an archived source in `sources/` into per-case TOML. All are
**merge-safe: they refresh only the `_zh` (original) fields and never clobber
translations or pointers.** One seeder per source format:

- `scripts/seed_from_source.py` — Gateless Gate, from Wikisource wikitext.
- `scripts/cbeta.py` — shared helpers for CBETA TEI: strips the scholarly
  apparatus (footnotes, the interlinear capping phrases 著語, variant readings),
  resolves gaiji, and yields `<p>/<head>/<lg>` blocks in document order.
- `scripts/seed_blue_cliff.py`, `scripts/seed_serenity.py` — Blue Cliff Record
  and Book of Serenity, from CBETA TEI, using `cbeta.py`. **Core depth only:**
  intro (垂示/示眾) + case (本則) + verse (頌); the prose commentary (評唱) and
  capping phrases are deliberately dropped.

Then:

- `build.py` — `data/*.toml` → static HTML/CSS/JS in `dist/`. Generates the home
  page, per-collection index, one page per case, an about page, and a
  client-side search index. Collections are auto-discovered (any `data/<slug>/`
  with a `collection.toml`).
- `deploy.sh` — builds, rsyncs `dist/` to `/var/www/koan` on the server, writes
  the nginx config on first run. TLS via certbot (one-time, after DNS).

## Sources & licensing

Originals come from public-domain editions. The Gateless Gate is from Chinese
Wikisource (PD-old). The Blue Cliff Record and Book of Serenity are from CBETA:
the **base text is the Taishō Tripiṭaka (public domain)**; CBETA's digital
edition is used with attribution (recorded in each `source_note`). The "originals
are public domain" claim holds for the base texts; translations are CC0.

## Architecture Rules

- **No build tools, no bundlers, no frameworks, no npm.** Python 3.11+ stdlib
  only (`tomllib`, `html`, `json`, `shutil`). The generator is the whole
  toolchain.
- Static output. Drop `dist/` on a server. Client-side search is one small
  vanilla-JS file over a generated JSON index — no search service.
- CSS is one hand-written stylesheet. System fonts only (CJK serif stack); no
  webfont dependency.
- Keep it readable: this is a literary site. Serif body, bilingual columns that
  stack on mobile, the pointer in its own callout.

## Adding a Collection

1. Archive the source in `sources/`.
2. Write a `scripts/seed_<name>.py` (use the existing seeders as templates;
   reuse `cbeta.py` for CBETA TEI) that emits `data/<slug>/NNN.toml`, merge-safe.
3. Hand-author `data/<slug>/collection.toml` (titles, compiler/date, source +
   license notes, `intro_en`, any label overrides).
4. `build.py` discovers it automatically.
