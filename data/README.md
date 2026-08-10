# Supplemental contribution datasets

## Ruku boundaries

`rukus.json` stores 558 global Ruku boundaries extracted from the `ruku_number`
metadata returned for all 6,236 verses by the Quran.com API v4 `by_page`
endpoint. It is kept separate from the repository's Quran text and databases so
the provenance and proposed schema can be reviewed independently before any
upstream database integration.

Each entry records the first and last verse IDs and keys, its page range, and
the Juz containing its first verse. Regenerate it from the locally downloaded
API response with:

```sh
python3 scripts/export_rukus.py
```

The raw API response remains under the ignored `output/` directory. Before an
upstream contribution, confirm attribution/licensing requirements and validate
the boundaries against another authoritative Ruku source.
