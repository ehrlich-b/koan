# 公案 · kōan

A public-domain repository of Zen kōan in their original language, paired with free English translations.

**Live:** [koan.ehrlich.dev](https://koan.ehrlich.dev)

The classic kōan collections are Classical Chinese texts composed eight or nine centuries ago — unambiguously public domain. Most good English translations, though, are still under copyright. This project pairs the public-domain originals with **new** translations released under [CC0](LICENSE), so the whole thing — original and translation alike — is free for anyone to use.

Each entry has three parts:

1. **Original** — the source text, transcribed from a public-domain edition and checked against it character by character.
2. **Translation** — faithful but readable.
3. **Pointer** — an oblique nudge giving the modern reader the context a monk in the original audience already had. Not an explanation; explaining a kōan ruins it.

## Collections

384 cases across six collections. All originals are in; translation has just begun.

| Collection | Original | Cases | Source |
|---|---|---|---|
| [The Gateless Gate](data/gateless-gate/) | 無門關 (Mumonkan), 1228 | 48 | Wikisource |
| [The Blue Cliff Record](data/blue-cliff-record/) | 碧巖錄 (Hekiganroku), c. 1125 | 100 | CBETA (T2003) |
| [The Book of Serenity](data/book-of-serenity/) | 從容錄 (Shōyōroku), 1224 | 100 | CBETA (T2004) |
| [The Record of Linji](data/record-of-linji/) | 臨濟錄 (Rinzai-roku) | 66 | CBETA (T1985) |
| [The Record of Zhaozhou](data/record-of-zhaozhou/) | 趙州真際禪師語錄 | 46 | CBETA (X1315) |
| [The Record of Layman Pang](data/record-of-layman-pang/) | 龐居士語錄 | 24 | CBETA (X1336) |

The first three are the classic kōan collections (case + commentary/verse). The
last three are recorded-sayings (語錄): continuous discourse and encounter
dialogue, segmented by editorial section rather than into numbered kōan. The
Iron Flute (鐵笛倒吹) was considered but isn't in CBETA — it survives only in a
modern Japanese collection — so it's omitted for now.

Originals from CBETA are the public-domain Taishō/Xuzangjing base text via
CBETA's digital edition (attributed in each collection's `source_note`).

## Layout

```
data/<collection>/
  collection.toml      metadata, prefaces, opening verse
  NN.toml              one file per case: original + translation + pointer
sources/               archived public-domain source text (provenance)
scripts/seed_from_source.py   (re)derive original text from sources/
build.py               data/*.toml -> static site in dist/
assets/                style.css, search.js (copied verbatim into dist/)
deploy.sh              build + rsync to koan.ehrlich.dev
```

No frameworks, no bundler, no npm. The generator is a single dependency-free Python script (3.11+ stdlib).

## Working on it

```
make serve      # build + serve at http://localhost:8048
make build      # generate dist/
make reseed     # refresh original text from sources/ (keeps translations)
make deploy     # build + publish to koan.ehrlich.dev
```

**To translate a case:** edit its `data/<collection>/NN.toml` and fill in the
`*_en` fields and `pointer`. Leave a field empty and the site shows the original
with a "translation not yet available" note. Re-running `make reseed` never
overwrites your English — it only refreshes the Chinese from `sources/`.

## License & attribution

Original texts are in the public domain. English translations and pointers are
released under **CC0 1.0 Universal** (see [LICENSE](LICENSE)) — no rights
reserved, no attribution required.

Gateless Gate original from [Chinese Wikisource](https://zh.wikisource.org/wiki/無門關)
(public domain), cross-referenceable with the Taishō Tripiṭaka vol. 48, no. 2005.
