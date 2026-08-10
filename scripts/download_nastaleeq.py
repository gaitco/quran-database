#!/usr/bin/env python3
"""Download the font-matched QPC Nastaleeq Hafs script from Quran.com."""

from __future__ import annotations

import argparse
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "output" / "qpc-nastaleeq-hafs-api.json"
URL = (
    "https://api.quran.com/api/v4/verses/by_page/"
    "{page}?fields=text_qpc_nastaleeq_hafs,text_qpc_hafs"
)


def fetch_page(page: int) -> list[dict]:
    request = urllib.request.Request(
        URL.format(page=page), headers={"User-Agent": "quran-database-exporter/1"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["verses"]


def download(output: Path) -> list[dict]:
    with ThreadPoolExecutor(max_workers=8) as executor:
        pages = executor.map(fetch_page, range(1, 605))
        verses = [verse for page in pages for verse in page]

    verses.sort(key=lambda verse: verse["id"])
    if len(verses) != 6236:
        raise ValueError(f"Expected 6,236 verses, found {len(verses)}")
    if [verse["id"] for verse in verses] != list(range(1, 6237)):
        raise ValueError("Nastaleeq verse IDs are not continuous")
    if any(not verse.get("text_qpc_nastaleeq_hafs") for verse in verses):
        raise ValueError("A verse is missing font-matched Nastaleeq Hafs text")
    if any(not verse.get("text_qpc_hafs") for verse in verses):
        raise ValueError("A verse is missing font-matched QPC Hafs text")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"verses": verses}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
        newline="\n",
    )
    return verses


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    verses = download(arguments.output)
    print(f"Downloaded {len(verses)} Nastaleeq Hafs verses to {arguments.output}")


if __name__ == "__main__":
    main()
