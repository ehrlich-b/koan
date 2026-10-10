"""Tests for scripts/seed_from_source.py — the pure text functions only.

Covers `clean`, `join_prose`, `join_verse`, `basic`, `literal`, and
`parse_cases`.  Deliberately never calls `write_koan` or `main` (those touch
the filesystem under data/), and every wikitext here is a hand-built Python
string — nothing reads sources/gateless-gate.zh.wikitext.
"""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import seed_from_source as sfs

FW = sfs.FW  # full-width / ideographic space U+3000 -- the verse field separator.


class TestClean(unittest.TestCase):
    def test_clean_strips_fw_space_tab_off_ends(self):
        # Exact case from the CONTEXT: `clean(FW + " 你好 " + FW)` -> "你好".
        self.assertEqual(sfs.clean(FW + " 你好 " + FW), "你好")

    def test_clean_leaves_embedded_whitespace_alone(self):
        # strip() with an explicit char set trims only the ENDS.  A newline and
        # a tab sitting INSIDE the text must survive untouched; only the FW
        # framing and the trailing space at the very edges come off.
        self.assertEqual(sfs.clean(FW + "a\n\tb " + FW), "a\n\tb")


class TestJoinProse(unittest.TestCase):
    def test_join_prose_joins_with_newline_drops_empty(self):
        # Exact case from the CONTEXT: the empty middle line vanishes entirely,
        # not even as a blank line.
        self.assertEqual(sfs.join_prose(["  line1  ", "", "  line2"]), "line1\nline2")

    def test_join_prose_all_empty_is_empty_string(self):
        self.assertEqual(sfs.join_prose(["", "  ", FW]), "")

    def test_join_prose_single_line_has_no_extra_newlines(self):
        self.assertEqual(sfs.join_prose(["  only  "]), "only")


class TestJoinVerse(unittest.TestCase):
    def test_join_verse_splits_fw_runs_into_multiple_lines(self):
        # Exact case from the CONTEXT: one input line yields THREE output
        # lines.  The double-FW run between 句二/句三 is a single `FW+` match,
        # so it produces no empty line in between.
        self.assertEqual(
            sfs.join_verse(["句一" + FW + "句二" + FW * 2 + "句三"]),
            "句一\n句二\n句三",
        )

    def test_join_verse_line_without_fw_passes_through(self):
        # No FW at all: one in, one out, unchanged (after end-trim).
        self.assertEqual(sfs.join_verse(["单独一行"]), "单独一行")

    def test_join_verse_all_fw_line_contributes_nothing(self):
        # A line made ENTIRELY of FW characters has no real content, so it
        # yields zero output lines (empties are filtered out).
        self.assertEqual(sfs.join_verse([FW, FW * 3]), "")
        self.assertEqual(sfs.join_verse([FW, "句一"]), "句一")


class TestBasic(unittest.TestCase):
    def test_basic_escapes_backslash_then_quote_in_order(self):
        # Pin the escaping ORDER of `basic`: backslash -> `\\` FIRST, double
        # quote -> `\"` SECOND.
        #
        # Input (raw literal):  he said "hi\there"
        # character by character:
        #   h e <sp> s a i d <sp> " h i \ t h e r e "
        #
        # Step 1 -- replace("\", "\\"): each single backslash doubles.
        #   he said "hi \ \ t h e r e "     (the `t` is untouched)
        #
        # Step 2 -- replace('"', '\\"'): each double quote gains a backslash.
        #   he said \ " h i \ \ t h e r e \ "
        #
        # Wrapped in surrounding quotes:
        #   " he said \ " h i \ \ t h e r e \ " "        ->  end chars: \ " "
        #
        # Expected string:  "he said \"hi\\there\""
        #   `\"` = backslash + quote (2 chars),  `\\` = two backslashes, and
        #   one literal `"` at the very start and very end -- so the string
        #   finishes with `\"` (escaped closing quote) then the wrapper `"`.
        inp = r'he said "hi\there"'
        expected = r'"he said \"hi\\there\""'
        self.assertEqual(sfs.basic(inp), expected)


class TestLiteral(unittest.TestCase):
    def test_literal_empty_is_exactly_triple_quote_newline_triple_quote(self):
        # Exact special case (not "is falsy"): no blank line between the
        # delimiters when s is empty.
        self.assertEqual(sfs.literal(""), "'''\n'''")

    def test_literal_wraps_multiline_with_triple_single_quotes(self):
        self.assertEqual(sfs.literal("a\nb"), "'''\na\nb\n'''")

    def test_literal_rejects_content_with_triple_single_quote(self):
        with self.assertRaises(AssertionError) as cm:
            sfs.literal("bad ''' content")
        self.assertEqual(str(cm.exception), "content contains triple-quote")


# One hand-built wikitext for the parse_cases tests.  Case 1 has the redundant
# echo line right under its header ("一　趙州狗子", which cleaned ends with
# the header's title); the dedup must drop it.  Case 2's first content line
# does NOT echo its title, so it must be kept.  A trailing non-numbered
# `==Notes==` section must never leak into case 2.
#
# Expected derivation, done by hand:
#   cases[0] number=1 title_zh="趙州狗子"
#     case_zh:        "僧問：狗子還有佛性也無？"
#     commentary_zh:  "參禪須透祖師關。"
#     verse_zh:       "狗子佛性，全提正令。"
#   cases[1] number=2 title_zh="百丈野狐"
#     case_zh:        "師每上堂，大眾立定。"
#     commentary_zh:  "不落因果，不昧因果。"
#     verse_zh:       "不落不昧，萬法一如。"
#   neither case may contain "Notes" or "This section".
WT = """==1. 趙州狗子==
一　趙州狗子
　　僧問：狗子還有佛性也無？
【無門曰】
　　參禪須透祖師關。
【頌曰】
　　狗子佛性，全提正令。
==2. 百丈野狐==
　　師每上堂，大眾立定。
【無門曰】
　　不落因果，不昧因果。
【頌曰】
　　不落不昧，萬法一如。
==Notes==
This section is not a numbered case.
"""


class TestParseCases(unittest.TestCase):
    def setUp(self):
        self.cases = sfs.parse_cases(WT)

    def test_drops_title_echo_line_from_case_zh(self):
        # The echoed "<numeral>　<title>" line right under the header must be
        # ABSENT -- case_zh starts on the real content.
        self.assertEqual(self.cases[0]["case_zh"], "僧問：狗子還有佛性也無？")
        self.assertNotIn("一　趙州狗子", self.cases[0]["case_zh"])

    def test_keeps_first_line_when_it_does_not_echo_title(self):
        # Differential check: case 2's first line does not end with the
        # header's title, so the dedup must NOT drop it.
        self.assertEqual(self.cases[1]["case_zh"], "師每上堂，大眾立定。")

    def test_segments_two_cases_and_excludes_trailing_section(self):
        self.assertEqual(len(self.cases), 2)
        self.assertEqual(self.cases[0]["number"], 1)
        self.assertEqual(self.cases[0]["title_zh"], "趙州狗子")
        self.assertEqual(self.cases[0]["commentary_zh"], "參禪須透祖師關。")
        self.assertEqual(self.cases[0]["verse_zh"], "狗子佛性，全提正令。")
        self.assertEqual(self.cases[1]["number"], 2)
        self.assertEqual(self.cases[1]["title_zh"], "百丈野狐")
        self.assertEqual(self.cases[1]["commentary_zh"], "不落因果，不昧因果。")
        self.assertEqual(self.cases[1]["verse_zh"], "不落不昧，萬法一如。")
        # Content past the first non-numbered `==...==` header is excluded.
        for case in self.cases:
            blob = "|".join([case["case_zh"], case["commentary_zh"], case["verse_zh"]])
            self.assertNotIn("Notes", blob)
            self.assertNotIn("This section", blob)


if __name__ == "__main__":
    unittest.main()
