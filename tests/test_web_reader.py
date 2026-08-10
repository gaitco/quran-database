import json
import hashlib
import unittest
from collections import Counter
from pathlib import Path

from scripts.export_web_data import validate
from scripts.import_nastaleeq import import_script
from scripts.export_rukus import export_rukus
from scripts.import_uthmani import import_script as import_uthmani


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data" / "quran.json"
NASTALEEQ_DATA = ROOT / "docs" / "data" / "nastaleeq.json"
NASTALEEQ_FONT = ROOT / "docs" / "fonts" / "KFGQPCNastaleeq-Regular.ttf"
UTHMANI_FONT = ROOT / "docs" / "fonts" / "UthmanicHafs_V22.ttf"
RUKUS = ROOT / "data" / "rukus.json"
WEB_RUKUS = ROOT / "docs" / "data" / "rukus.json"
UTHMANI_DATA = ROOT / "docs" / "data" / "uthmani.json"


class WebReaderDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DATA.read_text(encoding="utf-8"))
        cls.ayahs = [ayah for page in cls.payload["pages"] for ayah in page["ayahs"]]

    def test_export_passes_validation(self):
        validate(self.payload)

    def test_known_surah_ayah_counts(self):
        counts = Counter(ayah[0] for ayah in self.ayahs)
        self.assertEqual(counts[1], 7)
        self.assertEqual(counts[2], 286)
        self.assertEqual(counts[108], 3)
        self.assertEqual(counts[114], 6)

    def test_every_surah_is_represented(self):
        self.assertEqual({ayah[0] for ayah in self.ayahs}, set(range(1, 115)))

    def test_juz_and_quarter_hizb_ranges(self):
        self.assertEqual({ayah[3] for ayah in self.ayahs}, set(range(1, 31)))
        self.assertEqual({ayah[4] for ayah in self.ayahs}, set(range(1, 241)))

    def test_bismillah_is_already_embedded_in_source_text(self):
        bismillah_end = "ٱلرَّحِيمِ"
        first_ayahs = {ayah[0]: ayah[2] for ayah in self.ayahs if ayah[1] == 1}
        for surah_id in set(range(2, 115)) - {9}:
            self.assertLess(first_ayahs[surah_id].find(bismillah_end), 50, surah_id)
            self.assertGreaterEqual(first_ayahs[surah_id].find(bismillah_end), 0, surah_id)
        self.assertNotIn(bismillah_end, first_ayahs[9][:50])

    def test_static_reader_contract(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        javascript = (ROOT / "docs" / "app.js").read_text(encoding="utf-8")
        self.assertIn('<article id="mushaf-page" class="mushaf-page" lang="ar" dir="rtl"', html)
        self.assertIn('>Previous</button>', html)
        self.assertIn('>Next</button>', html)
        self.assertIn('fetch("data/quran.json")', javascript)
        self.assertIn('replace(/^سورة\\s+/u, "")', javascript)
        self.assertIn('fetch("data/uthmani.json")', javascript)
        self.assertIn('state.uthmani["1:1"].replace', javascript)
        self.assertNotIn('marker.textContent = `۝${arabicNumber(ayahNumber)}`', javascript)
        self.assertIn("appendSurahHeading(surahId)", javascript)
        self.assertIn("elements.number.textContent = String(page.number)", javascript)
        self.assertIn('fetch("data/nastaleeq.json")', javascript)
        self.assertIn('value="nastaleeq"', html)
        self.assertIn('id="juz-select"', html)
        self.assertIn('id="surah-select"', html)
        self.assertIn('class="page-header"', html)
        self.assertLess(html.index('for="surah-select"'), html.index('for="juz-select"'))
        self.assertLess(html.index('for="juz-select"'), html.index('id="next"'))
        self.assertLess(html.index('id="next"'), html.index('for="page-select"'))
        self.assertLess(html.index('for="page-select"'), html.index('id="previous"'))
        self.assertIn('elements.juzSelect.value = String(juz)', javascript)
        self.assertIn('elements.surahSelect.value = String(surahId)', javascript)
        self.assertIn('heading.dataset.surahId = String(surahId)', javascript)
        self.assertIn('heading.scrollIntoView({ block: "start", behavior: "instant" })', javascript)

    def test_nastaleeq_script_matches_all_ayah_references(self):
        nastaleeq = json.loads(NASTALEEQ_DATA.read_text(encoding="utf-8"))
        expected = {f"{ayah[0]}:{ayah[1]}" for ayah in self.ayahs}
        self.assertEqual(set(nastaleeq), expected)
        self.assertTrue(all(nastaleeq.values()))

    def test_nastaleeq_import_is_reproducible(self):
        source = ROOT / "output" / "qpc-nastaleeq-hafs-api.json"
        if source.exists():
            imported = import_script(source, ROOT / "output" / "nastaleeq-test.json")
            committed = json.loads(NASTALEEQ_DATA.read_text(encoding="utf-8"))
            self.assertEqual(imported, committed)

    def test_nastaleeq_font_checksum(self):
        digest = hashlib.sha256(NASTALEEQ_FONT.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "de174e33ae14cb581097940de298c8bb9cfa60f7a34d7d0ab0ba2bd5126f912c",
        )

    def test_uthmani_font_is_local_and_verified(self):
        digest = hashlib.sha256(UTHMANI_FONT.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "aa68bffce289b4c0ebac68e90502eb69e42356abcd1603cb2b8e99c2c723f145",
        )
        stylesheet = (ROOT / "docs" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('url("fonts/UthmanicHafs_V22.ttf")', stylesheet)
        self.assertIn('font-family: "QPC Hafs"', stylesheet)
        self.assertIn('.mushaf-page[data-script="uthmani"] .ayah-flow', stylesheet)
        self.assertIn('font-synthesis: none', stylesheet)

    def test_uthmani_script_matches_font_and_all_ayah_references(self):
        uthmani = json.loads(UTHMANI_DATA.read_text(encoding="utf-8"))
        expected = {f"{ayah[0]}:{ayah[1]}" for ayah in self.ayahs}
        self.assertEqual(set(uthmani), expected)
        self.assertEqual(
            uthmani["2:10"],
            "فِي قُلُوبِهِم مَّرَضٞ فَزَادَهُمُ ٱللَّهُ مَرَضٗاۖ وَلَهُمۡ عَذَابٌ أَلِيمُۢ بِمَا كَانُواْ يَكۡذِبُونَ\u00a0١٠",
        )
        self.assertNotIn("۟", uthmani["2:10"])

    def test_uthmani_import_is_reproducible(self):
        source = ROOT / "output" / "qpc-nastaleeq-hafs-api.json"
        if source.exists():
            imported = import_uthmani(source, ROOT / "output" / "uthmani-test.json")
            committed = json.loads(UTHMANI_DATA.read_text(encoding="utf-8"))
            self.assertEqual(imported, committed)

    def test_ruku_boundaries_are_complete_and_continuous(self):
        payload = json.loads(RUKUS.read_text(encoding="utf-8"))
        rukus = payload["rukus"]
        self.assertEqual(payload["ruku_count"], 558)
        self.assertEqual([ruku["id"] for ruku in rukus], list(range(1, 559)))
        self.assertEqual(rukus[0]["start_verse_key"], "1:1")
        self.assertEqual(rukus[-1]["end_verse_key"], "114:6")
        self.assertTrue(
            all(ruku["start_verse_id"] <= ruku["end_verse_id"] for ruku in rukus)
        )

    def test_ruku_export_is_reproducible(self):
        source = ROOT / "output" / "qpc-nastaleeq-hafs-api.json"
        if source.exists():
            generated = export_rukus(source, ROOT / "output" / "rukus-test.json")
            committed = json.loads(RUKUS.read_text(encoding="utf-8"))
            self.assertEqual(generated, committed)

    def test_reader_loads_and_marks_ruku_endings(self):
        self.assertEqual(
            json.loads(WEB_RUKUS.read_text(encoding="utf-8")),
            json.loads(RUKUS.read_text(encoding="utf-8")),
        )
        javascript = (ROOT / "docs" / "app.js").read_text(encoding="utf-8")
        stylesheet = (ROOT / "docs" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('fetch("data/rukus.json")', javascript)
        self.assertIn("rememberRukuEnd(verseNode, surahId, ayahNumber)", javascript)
        self.assertIn("elements.rukuMarkers.append(marker)", javascript)
        self.assertIn('marker.textContent = "ع"', javascript)
        self.assertIn(".ruku-marker {", stylesheet)
        self.assertIn("right: 0;", stylesheet)

    def test_nastaleeq_uses_font_matched_ayah_endings(self):
        nastaleeq = json.loads(NASTALEEQ_DATA.read_text(encoding="utf-8"))
        self.assertEqual(nastaleeq["1:1"], "بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيْمِ ١")
        self.assertEqual(nastaleeq["1:2"], "اَلْحَمْدُ لِلّٰهِ رَبِّ الْعٰلَمِيْنَ ٢ﶫ")
        # The mismatched generic script uses this PUA range for every ayah.
        self.assertFalse(any("\uf500" <= char <= "\uf5ff" for text in nastaleeq.values() for char in text))

    def test_nastaleeq_bismillah_mark_does_not_use_unsupported_font_glyph(self):
        javascript = (ROOT / "docs" / "app.js").read_text(encoding="utf-8")
        stylesheet = (ROOT / "docs" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('mark.className = "bismillah-mark nastaleeq-bismillah-mark"', javascript)
        self.assertIn(".bismillah-mark {", stylesheet)
        self.assertIn("width: .62em;", stylesheet)
        self.assertNotIn(
            '.mushaf-page[data-script="nastaleeq"] .bismillah-mark', stylesheet
        )
        self.assertIn('state.nastaleeq["1:1"].replace', javascript)
        self.assertNotIn("الرَّحْمٰنِ الرَّحِیْمِ", javascript)


if __name__ == "__main__":
    unittest.main()
