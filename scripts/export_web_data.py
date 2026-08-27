#!/usr/bin/env python3
"""Export the SQLite Quran distribution as compact, checksum-tied web JSON."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sqlite3
import tempfile
import unicodedata
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "quran.db.gz"
DEFAULT_OUTPUT = ROOT / "output" / "quran-web.json"
DEFAULT_MANIFEST = ROOT / "manifest" / "quran-arabic.manifest.json"

EXPECTED_SURAHS = 114
EXPECTED_AYAHS = 6236
EXPECTED_PAGES = 604
AYAH_FIELDS = [
    "id",
    "surahId",
    "numberInSurah",
    "text",
    "juzId",
    "rubId",
    "sajda",
]


def verse_digest(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text.strip()).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


@contextmanager
def open_database(source: Path) -> Iterator[sqlite3.Connection]:
    if not source.is_file():
        raise FileNotFoundError(f"Database not found: {source}")

    temporary: tempfile.TemporaryDirectory[str] | None = None
    database_path = source
    if source.suffix == ".gz":
        temporary = tempfile.TemporaryDirectory()
        database_path = Path(temporary.name) / "quran.db"
        with gzip.open(source, "rb") as compressed, database_path.open("wb") as db:
            shutil.copyfileobj(compressed, db)

    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()
        if temporary is not None:
            temporary.cleanup()


def read_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if len(manifest.get("verses", {})) != EXPECTED_AYAHS:
        raise ValueError("Text manifest does not contain 6,236 verse hashes")
    if not manifest.get("quran"):
        raise ValueError("Text manifest is missing its Quran root hash")
    return manifest


def build_payload(connection: sqlite3.Connection, manifest: dict) -> dict:
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("SQLite integrity check failed")

    surahs = [
        {
            "id": row["id"],
            "number": row["number"],
            "nameAr": row["name_ar"],
            "nameEn": row["name_en"],
            "meaningEn": row["name_en_translation"],
            "type": row["type"],
        }
        for row in connection.execute(
            "SELECT id, number, name_ar, name_en, name_en_translation, type "
            "FROM surahs ORDER BY id"
        )
    ]

    pages: list[dict] = []
    current_page: dict | None = None
    verse_hashes: list[str] = []
    rows = connection.execute(
        "SELECT id, surah_id, number_in_surah, text, page, juz_id, rub_id, sajda "
        "FROM ayahs ORDER BY id"
    )
    for row in rows:
        key = f"{row['surah_id']}:{row['number_in_surah']}"
        digest = verse_digest(row["text"])
        if manifest["verses"].get(key) != digest:
            raise ValueError(f"Ayah {key} does not match the text manifest")
        verse_hashes.append(digest)

        if current_page is None or current_page["number"] != row["page"]:
            current_page = {
                "number": row["page"],
                "startAyahId": row["id"],
                "endAyahId": row["id"],
                "ayahs": [],
            }
            pages.append(current_page)
        current_page["endAyahId"] = row["id"]
        current_page["ayahs"].append(
            [
                row["id"],
                row["surah_id"],
                row["number_in_surah"],
                row["text"],
                row["juz_id"],
                row["rub_id"],
                row["sajda"],
            ]
        )

    root_hash = hashlib.sha256("".join(verse_hashes).encode()).hexdigest()
    if root_hash != manifest["quran"]:
        raise ValueError("Exported Quran root hash does not match the text manifest")
    if len(surahs) != EXPECTED_SURAHS:
        raise ValueError(f"Expected 114 surahs, found {len(surahs)}")
    if len(verse_hashes) != EXPECTED_AYAHS:
        raise ValueError(f"Expected 6,236 ayahs, found {len(verse_hashes):,}")
    if [page["number"] for page in pages] != list(range(1, EXPECTED_PAGES + 1)):
        raise ValueError("Page numbers are not continuous from 1 through 604")

    return {
        "meta": {
            "formatVersion": "1.0",
            "kind": "quran-web-export",
            "source": "quran-database SQLite distribution",
            "quranTextSha256": root_hash,
            "surahCount": len(surahs),
            "ayahCount": len(verse_hashes),
            "pageCount": len(pages),
            "ayahFields": AYAH_FIELDS,
        },
        "surahs": surahs,
        "pages": pages,
    }


def export(source: Path, output: Path, manifest_path: Path) -> dict:
    manifest = read_manifest(manifest_path)
    with open_database(source) as connection:
        payload = build_payload(connection, manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    arguments = parser.parse_args()
    payload = export(arguments.source, arguments.output, arguments.manifest)
    print(
        f"Exported {payload['meta']['ayahCount']:,} ayahs across "
        f"{payload['meta']['pageCount']} pages to {arguments.output}"
    )


if __name__ == "__main__":
    main()
