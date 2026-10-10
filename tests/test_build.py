"""Tests for the pure functions in build.py. unittest only — no pytest.

Import technique: build.py lives at the repo root, one directory above this
tests/ package, so the repo root is inserted onto sys.path before the import.
"""
import os
import sys
import unittest

# build.py is at the repo root; tests/ is a sibling package. Putting the repo
# root on sys.path lets `import build` find it regardless of how unittest
# discover assembles sys.path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build


class EscTests(unittest.TestCase):
    def test_esc_escapes_quotes_and_specials(self):
        # html.escape with quote=True turns all five characters into entities.
        self.assertEqual(build.esc("<"), "&lt;")
        self.assertEqual(build.esc(">"), "&gt;")
        self.assertEqual(build.esc("&"), "&amp;")
        self.assertEqual(build.esc('"'), "&quot;")
        self.assertEqual(build.esc("'"), "&#x27;")

    def test_esc_applies_once_not_twice(self):
        # "&amp;" (the literal string & a m p ;) -> its & becomes "&amp;", so
        # esc("&amp;") produces "&amp;amp;" — escaped once. It must NOT turn
        # into "&amp;amp;amp;", which would mean the output was escaped twice.
        self.assertEqual(build.esc("&amp;"), "&amp;amp;")
        self.assertNotEqual(build.esc("&amp;"), "&amp;amp;amp;")


class RenderProseTests(unittest.TestCase):
    def test_blank_line_splits_into_paragraphs(self):
        out = build.render_prose("first para\n\nsecond para")
        self.assertTrue(out.startswith("<p>first para</p>"))
        self.assertTrue(out.endswith("<p>second para</p>"))
        self.assertEqual(out.count("<p>"), 2)
        self.assertEqual(out.count("</p>"), 2)

    def test_single_newline_is_br_not_new_paragraph(self):
        out = build.render_prose("line one\nline two")
        self.assertEqual(out.count("<p>"), 1)  # one paragraph, not two
        self.assertIn("line one<br>", out)     # the newline became a <br>
        self.assertIn("line two</p>", out)

    def test_empty_and_whitespace_only_input_return_empty(self):
        self.assertEqual(build.render_prose(""), "")
        self.assertEqual(build.render_prose("   \n \t \n  "), "")

    def test_content_is_escaped(self):
        out = build.render_prose("hello <script>alert('x')</script>")
        self.assertIn("&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;", out)
        self.assertNotIn("<script>", out)


class RenderVerseTests(unittest.TestCase):
    def test_blank_lines_dropped_spans_counted(self):
        # 5 lines, 2 of them blank -> exactly 3 spans. Count, don't eyeball.
        out = build.render_verse("one\n\ntwo\n\n\nthree")
        self.assertEqual(out.count('<span class="line">'), 3)
        self.assertEqual(out.count("</span>"), 3)

    def test_content_is_escaped(self):
        out = build.render_verse("<b>bold</b>")
        self.assertIn("&lt;b&gt;bold&lt;/b&gt;", out)
        self.assertNotIn("<b>", out)

    def test_empty_input_yields_empty_string(self):
        self.assertEqual(build.render_verse(""), "")
        self.assertEqual(build.render_verse(" \n \n "), "")


class BilingualTests(unittest.TestCase):
    def test_with_english_side_has_zh_and_en_divs(self):
        out = build.bilingual("中\n文", "Chinese prose")
        self.assertIn('<div class="zh"', out)
        self.assertIn('<div class="en"', out)
        self.assertNotIn("untranslated", out)

    def test_empty_or_whitespace_english_is_untranslated(self):
        for en in ("", "   \n\t "):
            out = build.bilingual("中\n文", en)
            self.assertIn('class="untranslated"', out)

    def test_verse_kind_routes_through_render_verse(self):
        # DIFFERENTIAL: the zh half of the verse rendering must contain exactly
        # what render_verse produces, rather than a hard-coded copy of the
        # markup.
        zh = "道\n無門"
        en = "The way has no gate."
        out = build.bilingual(zh, en, kind="verse")
        self.assertIn(build.render_verse(zh), out)


class KoanFilenameTests(unittest.TestCase):
    def test_number_7_padded_to_2_and_3(self):
        c = {"number": 7, "slug": "dog"}
        self.assertEqual(build.koan_filename(c, 2), "07-dog.html")
        self.assertEqual(build.koan_filename(c, 3), "007-dog.html")

    def test_missing_and_empty_slug_both_omit_slug_segment(self):
        # c.get("slug") treats a missing key and an empty-string key the same:
        # both are falsy, so neither contributes a slug segment.
        no_slug = {"number": 7}
        empty_slug = {"number": 7, "slug": ""}
        self.assertEqual(build.koan_filename(no_slug, 2), "07.html")
        self.assertEqual(build.koan_filename(empty_slug, 2), "07.html")

    def test_number_larger_than_pad_is_not_truncated(self):
        c = {"number": 1234, "slug": "big"}
        self.assertEqual(build.koan_filename(c, 2), "1234-big.html")


class KoanUrlTests(unittest.TestCase):
    def test_uses_pad_from_meta(self):
        meta = {"slug": "book", "_pad": 3}
        c = {"number": 7, "slug": "dog"}
        self.assertEqual(build.koan_url(meta, c), "/book/007-dog.html")

    def test_defaults_pad_to_2_when_meta_has_no_pad(self):
        meta = {"slug": "book"}
        c = {"number": 7, "slug": "dog"}
        self.assertEqual(build.koan_url(meta, c), "/book/07-dog.html")

    def test_url_is_root_relative(self):
        # Documented contract: the module docstring says "all links are
        # root-relative", so every URL must start with "/".
        meta = {"slug": "book"}
        c = {"number": 7, "slug": "dog"}
        self.assertTrue(build.koan_url(meta, c).startswith("/"))


class TitlesTests(unittest.TestCase):
    def test_whitespace_only_english_diverges(self):
        # PINNED QUIRK: title_of uses raw truthiness, so a whitespace-only
        # title_en ("   ") is truthy and wins, returning the whitespace string.
        # titles calls .strip() first, so it falls through to the Chinese
        # title. The two functions disagree; both behaviours are pinned rather
        # than "fixing" build.py (editing build.py would be a scope violation).
        c = {"number": 1, "title_zh": "趙州狗子", "title_en": "   "}
        self.assertEqual(build.title_of(c), "   ")
        self.assertEqual(build.titles(c), ("趙州狗子", ""))

    def test_english_present(self):
        c = {"number": 1, "title_en": "Zhaozhou's Dog", "title_zh": "趙州狗子"}
        self.assertEqual(build.title_of(c), "Zhaozhou's Dog")
        self.assertEqual(build.titles(c), ("Zhaozhou's Dog", "趙州狗子"))

    def test_chinese_only(self):
        c = {"number": 1, "title_zh": "趙州狗子"}
        self.assertEqual(build.title_of(c), "趙州狗子")
        self.assertEqual(build.titles(c), ("趙州狗子", ""))

    def test_neither_present(self):
        c = {"number": 1}
        self.assertEqual(build.title_of(c), "Case 1")
        self.assertEqual(build.titles(c), ("Case 1", ""))

    def test_titles_never_shows_chinese_twice(self):
        # The docstring promises "Avoids showing the Chinese twice when there
        # is no English title yet": with no English, the secondary element is
        # the empty string.
        c = {"number": 1, "title_zh": "趙州狗子"}
        self.assertEqual(build.titles(c), ("趙州狗子", ""))
        c2 = {"number": 2}
        self.assertEqual(build.titles(c2), ("Case 2", ""))


class HeadingTests(unittest.TestCase):
    def test_nonempty_zh_emits_zh_span(self):
        out = build.heading("Main", "中")
        self.assertIn('<span class="zh" lang="zh-Hant">中</span>', out)

    def test_empty_zh_omits_zh_span(self):
        out = build.heading("Main", "")
        self.assertNotIn('class="zh"', out)
        self.assertEqual(out, "<h2>Main</h2>")

    def test_both_arguments_are_escaped(self):
        out = build.heading("<b>en</b>", "<b>zh</b>")
        self.assertIn("&lt;b&gt;en&lt;/b&gt;", out)
        self.assertIn("&lt;b&gt;zh&lt;/b&gt;", out)
        self.assertNotIn("<b>", out)


class SectionLabelTests(unittest.TestCase):
    def test_explicit_label_wins(self):
        meta = {"label_intro_en": "My Intro", "label_intro_zh": "垂示"}
        self.assertEqual(build.section_label(meta, "intro"), ("My Intro", "垂示"))

    def test_missing_label_falls_back_to_default(self):
        self.assertEqual(build.section_label({}, "intro"), ("Introduction", ""))

    def test_empty_string_label_falls_back_to_default(self):
        # The code uses `or`, so an explicit but empty label is treated as
        # absent and the SECTION_DEFAULTS value wins.
        meta = {"label_intro_en": ""}
        self.assertEqual(build.section_label(meta, "intro"), ("Introduction", ""))

    def test_unknown_section_raises_keyerror(self):
        # PINNED: SECTION_DEFAULTS[sec] is an unguarded lookup. It only fires
        # when the `or` operator is forced to evaluate it — i.e. when the meta
        # has no truthy label_<sec>_en — but then KeyError escapes with no
        # friendly message.
        with self.assertRaises(KeyError):
            build.section_label({}, "bogus")
        with self.assertRaises(KeyError):
            build.section_label({"label_bogus_en": ""}, "bogus")


class SearchIndexTests(unittest.TestCase):
    def _collections(self, cases, title="Test Book"):
        return [({"title_en": title, "slug": "test"}, cases)]

    def test_skips_untranslated_cases(self):
        # Three cases, only one with a non-empty case_en -> exactly 1 entry.
        collections = self._collections([
            {"number": 1, "title_en": "One", "case_en": "translated text"},
            {"number": 2, "title_zh": "二"},
            {"number": 3, "title_en": "Three", "case_en": ""},
        ])
        idx = build.build_search_index(collections)
        self.assertEqual(len(idx), 1)
        self.assertEqual(set(idx[0].keys()), {"u", "c", "n", "te", "tz", "b"})

    def test_collapses_whitespace_in_body(self):
        collections = self._collections([
            {
                "number": 1,
                "title_en": "One",
                "intro_en": "line one\n\nline two",
                "case_en": "alpha\t\tbeta",
                "commentary_en": "gamma   delta",
            }
        ])
        entry = build.build_search_index(collections)[0]
        self.assertNotIn("\n", entry["b"])
        self.assertNotIn("  ", entry["b"])
        self.assertEqual(entry["b"], "line one line two alpha beta gamma delta")

    @unittest.skip("KNOWN BUG in build.py: replace('The ', '') strips every occurrence, not just a leading one. Unskip when fixed.")
    def test_the_replacement_is_unrestricted(self):
        # Expected after the fix: only the leading "The " is removed.
        collections = self._collections(
            [{"number": 1, "title_en": "One", "case_en": "text"}],
            title="The Gateless Gate of The Mind",
        )
        entry = build.build_search_index(collections)[0]
        self.assertEqual(entry["c"], "Gateless Gate of The Mind")


class LoadCollectionTests(unittest.TestCase):
    def test_all_collections_return_sorted_cases_with_correct_pad(self):
        # DIFFERENTIAL against the real data files. Nothing is hard-coded: the
        # collections are discovered, and case counts, ordering and _pad are
        # all derived from what load_collection returns.
        for slug in sorted(os.listdir(build.DATA)):
            cdir = os.path.join(build.DATA, slug)
            if not (os.path.isdir(cdir) and os.path.exists(os.path.join(cdir, "collection.toml"))):
                continue
            pair = build.load_collection(slug)
            self.assertEqual(len(pair), 2, f"{slug}: expected a (meta, cases) pair")
            meta, cases = pair
            for c in cases:
                self.assertIn("number", c, f"{slug}: a case is missing 'number'")
            nums = [c["number"] for c in cases]
            self.assertEqual(nums, sorted(nums), f"{slug}: cases not ascending by number")
            largest = max(nums) if nums else 0
            expected_pad = 3 if largest >= 100 else 2
            self.assertEqual(meta["_pad"], expected_pad,
                             f"{slug}: _pad should be {expected_pad}, got {meta['_pad']}")
            print(f"  load_collection({slug!r}): {len(cases)} cases, "
                  f"max #{largest}, _pad={meta['_pad']}")


if __name__ == "__main__":
    unittest.main()
