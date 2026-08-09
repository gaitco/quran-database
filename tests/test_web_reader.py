import json
import unittest
from collections import Counter
from pathlib import Path

from scripts.export_web_data import validate


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data" / "quran.json"


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
        self.assertIn('const BISMILLAH_END = "ٱلرَّحِيمِ"', javascript)
        self.assertIn("text.indexOf(BISMILLAH_END)", javascript)
        self.assertIn('bismillahMark.textContent = "۝"', javascript)
        self.assertIn('marker.textContent = `۝${arabicNumber(ayahNumber)}`', javascript)
        self.assertIn("appendSurahHeading(surahId)", javascript)
        self.assertIn("elements.number.textContent = String(page.number)", javascript)


if __name__ == "__main__":
    unittest.main()
