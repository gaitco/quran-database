from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests import load_script


exporter = load_script("export_web_data")


class WebDataExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "source.db"
        self.manifest = self.root / "manifest.json"
        self.output = self.root / "web.json"
        self._create_database()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _create_database(self) -> None:
        connection = sqlite3.connect(self.database)
        connection.executescript(
            """
            CREATE TABLE surahs (
                id INTEGER PRIMARY KEY, number INTEGER, name_ar TEXT,
                name_en TEXT, name_en_translation TEXT, type TEXT
            );
            CREATE TABLE ayahs (
                id INTEGER PRIMARY KEY, surah_id INTEGER,
                number_in_surah INTEGER, text TEXT, page INTEGER,
                juz_id INTEGER, rub_id INTEGER, sajda INTEGER
            );
            """
        )
        connection.executemany(
            "INSERT INTO surahs VALUES (?, ?, ?, ?, ?, ?)",
            [(number, number, f"ar-{number}", f"en-{number}", "meaning", "type")
             for number in range(1, 115)],
        )
        rows = []
        verse_hashes = {}
        surah_ayah_counts = {}
        for ayah_id in range(1, 6237):
            surah_id = min(114, (ayah_id - 1) * 114 // 6236 + 1)
            number_in_surah = surah_ayah_counts.get(surah_id, 0) + 1
            surah_ayah_counts[surah_id] = number_in_surah
            page = min(604, (ayah_id - 1) * 604 // 6236 + 1)
            text = f"text-{ayah_id}"
            rows.append((ayah_id, surah_id, number_in_surah, text, page, 1, 1, 0))
            verse_hashes[f"{surah_id}:{number_in_surah}"] = exporter.verse_digest(text)
        connection.executemany("INSERT INTO ayahs VALUES (?,?,?,?,?,?,?,?)", rows)
        connection.commit()
        connection.close()

        root_hash = hashlib.sha256("".join(verse_hashes.values()).encode()).hexdigest()
        self.manifest.write_text(
            json.dumps({"verses": verse_hashes, "quran": root_hash}),
            encoding="utf-8",
        )

    def test_exports_complete_checksum_tied_payload(self) -> None:
        payload = exporter.export(self.database, self.output, self.manifest)

        self.assertEqual(payload["meta"]["surahCount"], 114)
        self.assertEqual(payload["meta"]["ayahCount"], 6236)
        self.assertEqual(payload["meta"]["pageCount"], 604)
        self.assertEqual(payload["meta"]["ayahFields"], exporter.AYAH_FIELDS)
        self.assertEqual(payload["pages"][0]["startAyahId"], 1)
        self.assertEqual(payload["pages"][-1]["endAyahId"], 6236)
        self.assertEqual(payload["pages"][0]["ayahs"][0][:4], [1, 1, 1, "text-1"])
        self.assertEqual(
            json.loads(self.output.read_text(encoding="utf-8")), payload
        )

    def test_rejects_text_that_differs_from_manifest(self) -> None:
        connection = sqlite3.connect(self.database)
        connection.execute("UPDATE ayahs SET text = 'changed' WHERE id = 100")
        connection.commit()
        connection.close()

        with self.assertRaisesRegex(ValueError, "Ayah .* text manifest"):
            exporter.export(self.database, self.output, self.manifest)


if __name__ == "__main__":
    unittest.main()
