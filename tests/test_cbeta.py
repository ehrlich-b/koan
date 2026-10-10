"""Tests for scripts/cbeta.py — the shared CBETA TEI-cleaning helpers used by
every CBETA-sourced seeder (seed_blue_cliff.py, seed_serenity.py,
seed_record_of_*.py).

scripts/ is not a package (no __init__.py), so we stash it on sys.path and
import cbeta as a bare module. Every XML fixture below is a tiny hand-built
string parsed in memory with xml.etree.ElementTree; we never read a real
multi-megabyte sources/*.tei.xml file.
"""
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, "scripts")

import cbeta

TEI = cbeta.TEI
XML_ID = cbeta.XML_ID
NS = TEI.strip("{}")


def _p(fragment, gaiji=None):
    root = ET.fromstring(f'<p xmlns="{NS}">{fragment}</p>')
    return cbeta.text_of(root, gaiji or {})


def _body(fragment):
    return ET.fromstring(f'<body xmlns="{NS}">{fragment}</body>')


class CjkNumPositionalTest(unittest.TestCase):
    def test_positional_digits(self):
        # All char are digit-glyphs -> read positionally, digit by digit.
        cases = {
            "一〇〇": 100,   # 1,0,0 read positionally
            "一零三": 103,   # 1,0,3 (零 as zero)
            "〇一二": 12,    # 0,1,2 -> int("012")
            "零零": 0,       # 0,0
        }
        for s, expected in cases.items():
            with self.subTest(s=s):
                self.assertEqual(cbeta.cjk_num(s), expected)


class CjkNumStandardTest(unittest.TestCase):
    def test_standard_form(self):
        # Standard Chinese numeral grammar with _UNIT multipliers.
        cases = {
            "二十一": 21,          # 2*10 + 1
            "一百": 100,           # 1*100
            "一百二十三": 123,    # 1*100 + 2*10 + 3
            "三十五": 35,          # 3*10 + 5
            "五十": 50,            # 5*10
            "一千二百三十四": 1234,  # 1*1000 + 2*100 + 3*10 + 4
        }
        for s, expected in cases.items():
            with self.subTest(s=s):
                self.assertEqual(cbeta.cjk_num(s), expected)


class CollapseTest(unittest.TestCase):
    def test_strips_all_whitespace(self):
        # Mixed spaces, tabs and newlines all dropped.
        self.assertEqual(cbeta.collapse("A B\tC\nD"), "ABCD")

    def test_no_whitespace_unchanged(self):
        self.assertEqual(cbeta.collapse("無隔"), "無隔")

    def test_all_whitespace(self):
        self.assertEqual(cbeta.collapse(" \t\n "), "")


class ResolveTest(unittest.TestCase):
    def test_hex_codepoints(self):
        self.assertEqual(cbeta._resolve("U+4E00"), "一")
        self.assertEqual(cbeta._resolve("4E00"), "一")
        self.assertEqual(cbeta._resolve("0x4E00"), "一")

    def test_maximum_valid_codepoint(self):
        # 0x10FFFF is the largest valid Unicode codepoint.
        self.assertEqual(cbeta._resolve("10FFFF"), chr(0x10FFFF))

    def test_out_of_range_hex_falls_back(self):
        # 0xFFFFFF exceeds 0x10FFFF; chr() raises ValueError, caught -> "□".
        self.assertEqual(cbeta._resolve("FFFFFF"), "□")

    def test_non_hex_multi_char_falls_back(self):
        # 3-char string that is not a fullmatch of 4-6 hex digits -> len != 1 -> "□"
        self.assertEqual(cbeta._resolve("abc"), "□")

    def test_single_non_hex_char_passes_through(self):
        # len(text) == 1 branch returns the character itself.
        self.assertEqual(cbeta._resolve("龍"), "龍")


class TextOfApparatusTest(unittest.TestCase):
    def test_note_dropped_tail_kept(self):
        # <note> is dropped entirely; its tail text survives.
        self.assertEqual(_p("師云<note>此乃註解</note>也"), "師云也")

    def test_app_keeps_lemma_drops_reading(self):
        # <app><lem>/<rdg>: keep the lemma, drop the variant.
        self.assertEqual(_p("云<app><lem>趙州</lem><rdg>別本</rdg></app>也"), "云趙州也")

    def test_app_rdg_before_lem_same_result(self):
        # Child order must not matter: el.find(TEI+"lem") finds the lem regardless.
        self.assertEqual(_p("云<app><rdg>別本</rdg><lem>趙州</lem></app>也"), "云趙州也")

    def test_choice_prefers_corr_over_sic(self):
        self.assertEqual(_p("云<choice><sic>多</sic><corr>再</corr></choice>也"), "云再也")

    def test_choice_prefers_reg_over_orig(self):
        self.assertEqual(_p("云<choice><orig>弓</orig><reg>公</reg></choice>也"), "云公也")

    def test_choice_falls_back_to_first_kid(self):
        # No corr/reg -> the first child (sic) is kept.
        self.assertEqual(_p("云<choice><sic>多</sic><orig>弓</orig></choice>也"), "云多也")

    def test_g_resolved_via_gaiji(self):
        # # prefix stripped; resolved through the gaiji dict.
        self.assertEqual(_p("師<g ref=\"#CB001\"/>云", {"CB001": "龍"}), "師龍云")

    def test_g_with_empty_gaiji_falls_back(self):
        # Unknown/missing gaiji -> placeholder, does not raise KeyError.
        self.assertEqual(_p("師<g ref=\"#CB001\"/>云"), "師□云")


class BlocksTest(unittest.TestCase):
    def test_document_order_through_nested_containers(self):
        body = _body(
            "<div>"
            "<div><p>一</p></div>"
            "<head>題目</head>"
            "</div>"
            "<lg><l>春</l><l>夏</l></lg>"
            "<p>二</p>"
        )
        self.assertEqual(
            cbeta.blocks(body, {}),
            [
                ("p", "", "一"),
                ("head", "", "題目"),
                ("lg", "", "春\n夏"),
                ("p", "", "二"),
            ],
        )

    def test_drops_apparatus_and_preserves_rend(self):
        body = _body(
            "<div><p rend=\"italic\">師<note>註</note>云</p></div>"
            "<lg><l>甲</l><l>乙</l></lg>"
        )
        self.assertEqual(
            cbeta.blocks(body, {}),
            [
                ("p", "italic", "師云"),
                ("lg", "", "甲\n乙"),
            ],
        )


class LoadGaijiTest(unittest.TestCase):
    def test_unicode_mapping_wins(self):
        root = ET.fromstring(
            f'<TEI xmlns="{NS}"><charDecl>'
            '<char xml:id="CB004">'
            '<mapping type="Romanized">4E03</mapping>'
            '<mapping type="unicode">4E04</mapping>'
            "</char>"
            "</charDecl></TEI>"
        )
        # `unicode` is preferred even when it appears after another mapping type.
        self.assertEqual(cbeta.load_gaiji(root), {"CB004": chr(0x4E04)})

    def test_normal_unicode_fallback_first_wins(self):
        root = ET.fromstring(
            f'<TEI xmlns="{NS}"><charDecl>'
            '<char xml:id="CB002">'
            '<mapping type="normal_unicode">4E01</mapping>'
            '<mapping type="Romanized">4E02</mapping>'
            "</char>"
            "</charDecl></TEI>"
        )
        # No `unicode`: the FIRST of normal_unicode/Romanized encountered wins.
        self.assertEqual(cbeta.load_gaiji(root), {"CB002": chr(0x4E01)})

    def test_no_recognized_mapping_skipped(self):
        root = ET.fromstring(
            f'<TEI xmlns="{NS}"><charDecl>'
            '<char xml:id="CB003">'
            '<mapping type="malayalam">junk</mapping>'
            '<mapping type="long">junk2</mapping>'
            "</char>"
            "</charDecl></TEI>"
        )
        # Neither unicode nor normal_unicode/Romanized -> not picked, no error.
        self.assertEqual(cbeta.load_gaiji(root), {})

    def test_char_without_id_skipped(self):
        root = ET.fromstring(
            f'<TEI xmlns="{NS}"><charDecl>'
            '<char><mapping type="unicode">4E50</mapping></char>'
            "</charDecl></TEI>"
        )
        # No xml:id -> skipped, not raised.
        self.assertEqual(cbeta.load_gaiji(root), {})

    def test_full_priority_example(self):
        root = ET.fromstring(
            f'<TEI xmlns="{NS}"><charDecl>'
            '<char xml:id="CB001">'
            '<mapping type="unicode">4E00</mapping>'
            "</char>"
            '<char xml:id="CB002">'
            '<mapping type="normal_unicode">4E01</mapping>'
            '<mapping type="Romanized">4E02</mapping>'
            "</char>"
            '<char xml:id="CB004">'
            '<mapping type="Romanized">4E03</mapping>'
            '<mapping type="unicode">4E04</mapping>'
            "</char>"
            "</charDecl></TEI>"
        )
        self.assertEqual(
            cbeta.load_gaiji(root),
            {"CB001": chr(0x4E00), "CB002": chr(0x4E01), "CB004": chr(0x4E04)},
        )


if __name__ == "__main__":
    unittest.main()
