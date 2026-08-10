#!/usr/bin/env python3
"""Validate and compact the QPC Nastaleeq Quran script for the web reader."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "output" / "qpc-nastaleeq-hafs-api.json"
DEFAULT_OUTPUT = ROOT / "docs" / "data" / "nastaleeq.json"


def import_script(source: Path, output: Path) -> dict[str, str]:
    payload = json.loads(source.read_text(encoding="utf-8"))
    verses = payload.get("verses", [])
    if len(verses) != 6236:
        raise ValueError(f"Expected 6,236 Nastaleeq verses, found {len(verses)}")

    result: dict[str, str] = {}
    for expected_id, verse in enumerate(verses, start=1):
        if verse.get("id") != expected_id:
            raise ValueError(f"Unexpected verse ID at position {expected_id}")
        key = verse.get("verse_key")
        text = verse.get("text_qpc_nastaleeq_hafs")
        if not key or not text:
            raise ValueError(f"Missing key or text for verse ID {expected_id}")
        if key in result:
            raise ValueError(f"Duplicate verse key: {key}")
        result[key] = text

    if next(iter(result)) != "1:1" or next(reversed(result)) != "114:6":
        raise ValueError("Unexpected first or last Nastaleeq verse")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
        newline="\n",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = import_script(arguments.source, arguments.output)
    print(f"Imported {len(result)} Nastaleeq verses to {arguments.output}")


if __name__ == "__main__":
    main()
