"""Unit tests for the pure string helpers in build.py.

Every function tested here is pure string-in/string-out: no file I/O, no
randomness, no network, no dependence on wall-clock time. Importing build is
safe because the module only calls main() under __main__.
"""

import unittest

import build


class TestEsc(unittest.TestCase):
    def test_escapes_quotes_and_special_chars(self):
        self.assertEqual(
            build.esc('<a> & "quote" \'apos\''),
            '&lt;a&gt; &amp; &quot;quote&quot; &#x27;apos&#x27;',
        )

    def test_does_not_double_escape(self):
        self.assertEqual(build.esc("a&b"), "a&amp;b")


class TestRenderProse(unittest.TestCase):
    def test_blank_lines_split_paragraphs_and_newlines_become_br(self):
        self.assertEqual(
            build.render_prose("Para one line1\nline2\n\nPara two"),
            "<p>Para one line1<br>\nline2</p>\n<p>Para two</p>",
        )

    def test_empty_input_returns_empty_string(self):
        self.assertEqual(build.render_prose(""), "")
        self.assertEqual(build.render_prose("   \n  \n"), "")

    def test_single_paragraph_produces_exactly_one_p(self):
        self.assertEqual(build.render_prose("Just one line"), "<p>Just one line</p>")


class TestRenderVerse(unittest.TestCase):
    def test_blank_lines_dropped_no_extra_spans(self):
        self.assertEqual(
            build.render_verse("line a\nline b\n\nline c"),
            '<span class="line">line a</span>\n'
            '<span class="line">line b</span>\n'
            '<span class="line">line c</span>\n',
        )

    def test_lines_are_html_escaped(self):
        out = build.render_verse("a < b & c")
        self.assertIn("a &lt; b &amp; c", out)
        self.assertNotIn("a < b & c", out)


class TestKoanFilename(unittest.TestCase):
    def test_slug_appended_with_padding(self):
        self.assertEqual(build.koan_filename({"number": 7, "slug": "foo"}), "07-foo.html")

    def test_empty_slug_yields_no_suffix(self):
        self.assertEqual(build.koan_filename({"number": 7, "slug": ""}), "07.html")

    def test_missing_slug_yields_no_suffix(self):
        self.assertEqual(build.koan_filename({"number": 7}), "07.html")

    def test_custom_pad(self):
        self.assertEqual(build.koan_filename({"number": 123, "slug": "bar"}, pad=3), "123-bar.html")


class TestTitles(unittest.TestCase):
    def test_neither_title_falls_back_to_case_number(self):
        self.assertEqual(build.titles({"title_en": "", "title_zh": "", "number": 5}), ("Case 5", ""))

    def test_chinese_only_as_main_title(self):
        self.assertEqual(build.titles({"title_en": "", "title_zh": "趙州", "number": 5}), ("趙州", ""))

    def test_english_wins_with_chinese_secondary(self):
        self.assertEqual(build.titles({"title_en": "Joshu", "title_zh": "趙州", "number": 5}), ("Joshu", "趙州"))


class TestTitleOf(unittest.TestCase):
    def test_falls_back_to_case_number(self):
        self.assertEqual(build.title_of({"title_en": "", "title_zh": "", "number": 9}), "Case 9")

    def test_title_en_returned_directly(self):
        self.assertEqual(build.title_of({"title_en": "Joshu", "title_zh": "趙州", "number": 9}), "Joshu")


class TestSectionLabel(unittest.TestCase):
    def test_chinese_label_present_no_english_override(self):
        self.assertEqual(build.section_label({"label_verse_zh": "頌"}, "verse"), ("Verse", "頌"))

    def test_no_override_uses_default(self):
        self.assertEqual(build.section_label({}, "commentary"), ("Commentary", ""))

    def test_english_override_beats_default(self):
        self.assertEqual(
            build.section_label({"label_intro_en": "Preface", "label_intro_zh": "垂示"}, "intro"),
            ("Preface", "垂示"),
        )


class TestHeading(unittest.TestCase):
    def test_zh_span_present_when_zh_nonempty(self):
        out = build.heading("Wumen's Commentary", "無門曰")
        self.assertIn('class="zh"', out)

    def test_zh_span_absent_when_zh_empty(self):
        out = build.heading("Wumen's Commentary", "")
        self.assertNotIn('class="zh"', out)


class TestBilingual(unittest.TestCase):
    def test_nonempty_en_renders_both_panes(self):
        out = build.bilingual("一", "one")
        self.assertIn('<div class="zh" lang="zh-Hant"><p>一</p></div>', out)
        self.assertIn('<div class="en"><p>one</p></div>', out)

    def test_empty_en_shows_untranslated_notice(self):
        out = build.bilingual("一", "  ")
        self.assertIn(
            '<p class="untranslated">English translation not yet available — contributions welcome.</p>',
            out,
        )

    def test_verse_kind_emits_line_spans(self):
        out = build.bilingual("一\n二", "one\ntwo", kind="verse")
        self.assertIn('class="line"', out)
        self.assertNotIn("<p>", out)


if __name__ == "__main__":
    unittest.main()
