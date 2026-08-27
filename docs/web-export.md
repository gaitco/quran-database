# Web JSON export

`scripts/export_web_data.py` converts the compressed SQLite distribution into
one compact UTF-8 JSON file suitable for static sites and browser applications.
The generated file is ignored and is not a second tracked Quran-text source.

## Generate

```sh
python3 scripts/export_web_data.py
```

Defaults:

| Input or output | Path |
| --- | --- |
| SQLite source | `quran.db.gz` |
| Text integrity manifest | `manifest/quran-arabic.manifest.json` |
| Generated JSON | `output/quran-web.json` |

An uncompressed SQLite source and a different destination can be selected:

```sh
python3 scripts/export_web_data.py --source quran.db --output output/quran.json
```

## Format

The top-level object contains `meta`, `surahs`, and `pages`. `meta` records the
format version, row counts, ordered ayah-field names, and the Quran root SHA-256
from the tracked text manifest.

Each Surah is an object with `id`, `number`, `nameAr`, `nameEn`, `meaningEn`, and
`type`. Each page contains its number, inclusive global ayah-ID range, and an
`ayahs` array. For compactness, each ayah is an array whose positions are named
by `meta.ayahFields`:

```json
{
  "ayahFields": [
    "id", "surahId", "numberInSurah", "text", "juzId", "rubId", "sajda"
  ]
}
```

Consumers should read the field list rather than silently assuming that a
future format version retains the same positions.

## Integrity checks

The exporter stops without writing output unless all of these checks pass:

- SQLite `integrity_check` reports `ok`;
- exactly 114 Surahs and 6,236 ayahs are present;
- page numbers are continuous from 1 through 604;
- every ayah matches its verse hash in the tracked manifest;
- the rollup of all verse hashes matches the manifest Quran root.

Text is copied exactly from SQLite into JSON. Unicode normalization is used
only while calculating the established manifest hashes; it does not rewrite
the exported text.
