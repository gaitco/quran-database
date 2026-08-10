#!/usr/bin/env python3
"""Import font-matched QPC Hafs text for the static reader."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "output" / "qpc-nastaleeq-hafs-api.json"
DEFAULT_OUTPUT = ROOT / "docs" / "data" / "uthmani.json"


def import_script(source: Path, output: Path) -> dict[str, str]:
    verses = json.loads(source.read_text(encoding="utf-8"))["verses"]
    script = {verse["verse_key"]: verse["text_qpc_hafs"] for verse in verses}
    if len(script) != 6236 or any(not text for text in script.values()):
        raise ValueError("Expected font-matched QPC Hafs text for 6,236 verses")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(script, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
        newline="\n",
    )
    return script


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    script = import_script(arguments.source, arguments.output)
    print(f"Imported {len(script)} QPC Hafs verses to {arguments.output}")


if __name__ == "__main__":
    main()
