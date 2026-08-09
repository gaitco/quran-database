#!/usr/bin/env python3
"""Export the bundled SQLite database for the static Quran reader."""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "quran.db.gz"
DEFAULT_OUTPUT = ROOT / "docs" / "data" / "quran.json"


def validate(payload: dict) -> None:
    """Fail if the browser export does not contain the expected Quran data."""
    surahs = payload["surahs"]
    pages = payload["pages"]
    ayahs = [ayah for page in pages for ayah in page["ayahs"]]

    if len(surahs) != 114:
        raise ValueError(f"Expected 114 surahs, found {len(surahs)}")
    if len(pages) != 604:
        raise ValueError(f"Expected 604 pages, found {len(pages)}")
    if [page["number"] for page in pages] != list(range(1, 605)):
        raise ValueError("Page numbers are not continuous from 1 through 604")
    if len(ayahs) != 6236:
        raise ValueError(f"Expected 6,236 ayahs, found {len(ayahs)}")
    if any(not ayah[2] for ayah in ayahs):
        raise ValueError("An ayah has empty Arabic text")

    references = [(ayah[0], ayah[1]) for ayah in ayahs]
    if len(references) != len(set(references)):
        raise ValueError("Duplicate surah/ayah reference found")
    if references[0] != (1, 1) or references[-1] != (114, 6):
        raise ValueError("Unexpected first or last ayah")
    if {ayah[3] for ayah in ayahs} != set(range(1, 31)):
        raise ValueError("Expected juz identifiers 1 through 30")
    if {ayah[4] for ayah in ayahs} != set(range(1, 241)):
        raise ValueError("Expected quarter-hizb identifiers 1 through 240")


def export(source: Path, output: Path) -> dict:
    """Read the compressed database and write compact, UTF-8 JSON."""
    if not source.is_file():
        raise FileNotFoundError(f"Database archive not found: {source}")

    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "quran.db"
        with gzip.open(source, "rb") as compressed, database_path.open("wb") as database:
            shutil.copyfileobj(compressed, database)

        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError(f"SQLite integrity check failed: {integrity}")

            surahs = [
                {
                    "id": row["id"],
                    "nameAr": row["name_ar"],
                    "nameEn": row["name_en"],
                    "meaningEn": row["name_en_translation"],
                }
                for row in connection.execute(
                    "SELECT id, name_ar, name_en, name_en_translation "
                    "FROM surahs ORDER BY id"
                )
            ]

            pages: list[dict] = []
            current_page = None
            rows = connection.execute(
                """
                SELECT page, surah_id, number_in_surah, text, juz_id, hizb_id
                FROM ayahs
                ORDER BY page, id
                """
            )
            for row in rows:
                if current_page is None or current_page["number"] != row["page"]:
                    current_page = {"number": row["page"], "ayahs": []}
                    pages.append(current_page)
                current_page["ayahs"].append(
                    [
                        row["surah_id"],
                        row["number_in_surah"],
                        row["text"],
                        row["juz_id"],
                        row["hizb_id"],
                    ]
                )
        finally:
            connection.close()

    payload = {"schemaVersion": 1, "surahs": surahs, "pages": pages}
    validate(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
        newline="\n",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    payload = export(arguments.source, arguments.output)
    ayah_count = sum(len(page["ayahs"]) for page in payload["pages"])
    print(
        f"Exported {ayah_count} ayahs across {len(payload['pages'])} pages "
        f"to {arguments.output}"
    )


if __name__ == "__main__":
    main()
