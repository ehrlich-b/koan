"""Tests for scripts/seed_record_of_zhaozhou.py.

Covers the two locally-maintained string helpers (basic/lit) against the
near-identical copies in seed_from_source.py (drift check), title_for_body's
ordering, and — the main event — segment()'s block-segmentation state machine.

segment() can only read its block sequence via the module-level
zhaozhou_blocks(), which parses the real 3.4MB CBETA TEI file under sources/
(and write_case/main write real files into data/). We never call the real
zhaozhou_blocks, write_case, or main. Instead every scenario monkeypatches
seed_record_of_zhaozhou.zhaozhou_blocks to return a small hand-built list and
restores the original in tearDown, so the module is always left clean even
though each test process is short-lived.
"""

import sys
import unittest

sys.path.insert(0, "scripts")

import seed_record_of_zhaozhou as z  # noqa: E402   (sys.path set above)
import seed_from_source  # noqa: E402


class TestTitleForBody(unittest.TestCase):
    def test_sizhong(self):
        # "示眾" present within the first 8 chars -> 示眾
        self.assertEqual(z.title_for_body("示眾云：莫造作，作則有業。"), "示眾")

    def test_shangtang(self):
        # "上堂" present within the first 8 chars (and not 示眾) -> 上堂
        self.assertEqual(z.title_for_body("上堂云：心即佛，佛即心。"), "上堂")

    def test_neither(self):
        self.assertEqual(z.title_for_body("僧問趙州如何是祖師西來意？"), "")

    def test_sizhong_wins_over_shangtang(self):
        # Both substrings fit in the first 8 chars; 示眾 is checked first.
        self.assertEqual(z.title_for_body("示眾上堂云：師良久。"), "示眾")


class TestBasicLitNoDrift(unittest.TestCase):
    STRINGS = (
        "趙州真際禪師諱從諗",
        '僧曰："如何是佛？"又曰："一\\二"',
        "",
        "第一行\n第二行\n\t縮排的詩句",
    )

    def test_basic_matches_seed_from_source(self):
        for s in self.STRINGS:
            with self.subTest(repr(s)):
                self.assertEqual(z.basic(s), seed_from_source.basic(s))

    def test_lit_matches_seed_from_source(self):
        for s in self.STRINGS:
            with self.subTest(repr(s)):
                self.assertEqual(z.lit(s), seed_from_source.literal(s))


class TestSegment(unittest.TestCase):
    # Hand-built (kind, rend, text) block sequences fed to segment() via a
    # monkeypatched zhaozhou_blocks. The original is restored in tearDown.
    def setUp(self):
        self._saved = z.zhaozhou_blocks  # saved in setUp, restored in tearDown
        self._bl = None

    def tearDown(self):
        z.zhaozhou_blocks = self._saved

    def _segment(self, bl):
        self._bl = bl
        z.zhaozhou_blocks = lambda: bl
        return z.segment()

    def test_full_trace_reproduces_verified_result(self):
        # One 11-block sequence exercising every rule: the very first prose
        # block becomes 行狀; a normal head + prose + inline continuation folds
        # the inline line into the previous case; a 十二時歌 verse head collects
        # two lines joined by \n; a DROP_HEADS head suppresses its following
        # paragraph; a final normal head + prose opens 上堂.
        bl = [
            ("p", "", "趙州真際禪師諱從諗，曹州郝鄉人也。"),
            ("head", "", "示眾"),
            ("p", "", "示眾云：莫造作，作則有業。"),
            ("p", "inline", "僧問：如何是佛？"),
            ("head", "", "十二時歌"),
            ("p", "", "雞鳴丑，睡起來。"),
            ("p", "", "桑公催起不得睡。"),
            ("head", "", "附趙王與師作真贊"),
            ("p", "", "紫磨金色相堂堂。"),
            ("head", "", "上堂"),
            ("p", "", "上堂云：金佛不度爐，木佛不度火。"),
        ]
        got = self._segment(bl)
        expected = [
            {"title_zh": "行狀",
             "case": "趙州真際禪師諱從諗，曹州郝鄉人也。",
             "num": 1},
            {"title_zh": "示眾",
             "case": "示眾云：莫造作，作則有業。\n僧問：如何是佛？",
             "num": 2},
            {"title_zh": "十二時歌",
             "case": "雞鳴丑，睡起來。\n桑公催起不得睡。",
             "num": 3},
            {"title_zh": "上堂",
             "case": "上堂云：金佛不度爐，木佛不度火。",
             "num": 4},
        ]
        self.assertEqual(got, expected)
        self.assertEqual([p["num"] for p in got], [1, 2, 3, 4])
        # The other-hands encomium is dropped, never making it into any case.
        self.assertNotIn("紫磨金色相堂堂。",
                         "".join(p["case"] for p in got))

    def test_drop_heads_suppression_is_cleared_by_next_head(self):
        # A DROP_HEADS head suppresses its content; a subsequent normal head
        # clears the suppression so its content is kept (not sticky for the
        # rest of the document).
        bl = [
            ("p", "", "行狀段"),
            ("head", "", "附趙王與師作真贊"),
            ("p", "", "被丟棄的附錄"),
            ("head", "", "上堂"),
            ("p", "", "上堂云：心即是佛。"),
        ]
        got = self._segment(bl)
        expected = [
            {"title_zh": "行狀", "case": "行狀段", "num": 1},
            {"title_zh": "上堂", "case": "上堂云：心即是佛。", "num": 2},
        ]
        self.assertEqual(got, expected)
        self.assertNotIn("被丟棄的附錄",
                         "".join(p["case"] for p in got))

    def test_verse_lines_accumulate_joined_by_newline(self):
        # A VERSE_HEADS head followed by 3 separate p blocks: all three are
        # kept, in order, joined by \n (not just the last, not concatenated
        # without separators).
        bl = [
            ("p", "", "行狀段"),
            ("head", "", "十二時歌"),
            ("p", "", "雞鳴丑。"),
            ("p", "", "卯時天。"),
            ("p", "", "辰時雪。"),
        ]
        got = self._segment(bl)
        verse = got[1]
        self.assertEqual(verse["title_zh"], "十二時歌")
        self.assertEqual(verse["case"], "雞鳴丑。\n卯時天。\n辰時雪。")

    def test_num_is_1_indexed_and_reflects_passage_order(self):
        # Derive from a small fresh sequence: 行狀, 上堂, 十二時歌.
        bl = [
            ("p", "", "行狀段"),
            ("head", "", "上堂"),
            ("p", "", "上堂云：第一段。"),
            ("head", "", "十二時歌"),
            ("p", "", "雞鳴丑。"),
        ]
        got = self._segment(bl)
        self.assertEqual([p["num"] for p in got], [1, 2, 3])
        self.assertEqual(
            {p["num"]: p["title_zh"] for p in got},
            {1: "行狀", 2: "上堂", 3: "十二時歌"},
        )


if __name__ == "__main__":
    unittest.main()
