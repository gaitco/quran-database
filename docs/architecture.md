# Architecture

Quran Database is currently a data distribution and conversion repository. Its
core asset is a MySQL dump; two Python converters derive enriched SQLite and
PostgreSQL databases from that dump. An API and container orchestration are
roadmap items, not part of the current architecture.

## Data flow

```text
data/quran.sql.zip
        |
        | extract to repository-root quran.sql
        |
        +----------------------+-------------------------+
        |                      |                         |
        v                      v                         v
 direct MySQL import   convert_to_sqlite.py    convert_to_postgres.py
        |                      |                         |
        v                      v                         v
 MySQL source model       quran.db             PostgreSQL database
                       enriched model           enriched model

quran.db.gz
    prebuilt compressed SQLite distribution
```

The converters use a line-oriented parser so the large SQL dump can be
processed without reading the whole file into memory. Both expect the extracted
file at `./quran.sql`. SQLite writes `./quran.db`; PostgreSQL connects to an
existing database using the standard `PGHOST`, `PGPORT`, `PGUSER`,
`PGPASSWORD`, and `PGDATABASE` environment variables.

The MySQL dump is the input format as supplied. The SQLite and PostgreSQL
converters create a related, enriched model with lookup tables, indexes,
constraints, and views. These models should therefore be compared deliberately
rather than assumed to be byte-for-byte or DDL-equivalent.

## Repository layout

| Path | Responsibility |
| --- | --- |
| `data/quran.sql.zip` | Versioned source dump used for conversion |
| `quran.db.gz` | Prebuilt compressed SQLite distribution |
| `convert_to_sqlite.py` | MySQL-dump parser and SQLite schema/import pipeline |
| `convert_to_postgres.py` | MySQL-dump parser and PostgreSQL schema/import pipeline |
| `schema/<database>/schema.sql` | Generated, readable schema reference per database |
| `scripts/export_schema.py` | Regenerates those references |
| `manifest/quran-arabic.manifest.json` | Verse-level SHA-256 hashes of the Arabic text |
| `scripts/checksum_text.py` | Generates and verifies that manifest |
| `data/rukus.json` | Supplemental Ruku boundary dataset (Quran Foundation convention) |
| `data/README.md` | Format, provenance, and licensing notes for supplemental datasets |
| `scripts/export_rukus.py` | Fetches and regenerates `data/rukus.json` |
| `scripts/export_web_data.py` | Generates checksum-tied, compact web JSON from SQLite |
| `docs/web-export.md` | Documents the generated web JSON format and integrity checks |
| `tests/` | Unit tests for the converters and the checksum tooling |
| `docs/` | Design and operational documentation |
| `output/` | Ignored location reserved for generated output |

The schema reference files are generated, never hand-edited. `schema/sqlite` and
`schema/postgres` are extracted from the converters, which remain authoritative;
`schema/mysql` is extracted from the source dump. Run `just schema` after changing
a converter — CI regenerates them and fails on any diff.

## Enriched data model

```text
juzs                 surahs
  |                     |
  | descriptive         | 1
  | ranges              |
  v                     | many
hizbs                ayahs 1 -------- many ayah_edition many -------- 1 editions
                        |
                        +-- page, juz_id, rub_id, sajda
                        |
                        +-- pages (604 descriptive ayah ranges)
```

The enriched SQLite and PostgreSQL targets contain seven tables:

| Table | Purpose | Expected rows |
| --- | --- | ---: |
| `surahs` | Surah identity, Arabic and English names, revelation type | 114 |
| `ayahs` | Arabic ayah text and navigation metadata | 6,236 |
| `editions` | Translation or edition metadata | 134 |
| `ayah_edition` | Text for each ayah and edition pairing | 835,624 |
| `juzs` | Thirty juz lookup records with ayah ranges | 30 |
| `hizbs` | Sixty hizb lookup records with ayah ranges | 60 |
| `pages` | Madinah Mushaf page lookup records with ayah ranges | 604 |

`ayah_edition` is the high-volume junction between `ayahs` and `editions`.
Indexes support common navigation by surah, juz, hizb, page, ayah number, and
sajdah status, plus translation lookups by ayah and edition.

Two convenience views sit above the tables:

- `surah_stats` aggregates ayah counts and ID ranges per surah.
- `ayah_with_translation` joins Arabic ayahs to edition text and metadata.

## Relationships and domain caveats

The enforced relationships in the current enriched schema are:

- `ayahs.surah_id` to `surahs.id`;
- `ayah_edition.ayah_id` to `ayahs.id`;
- `ayah_edition.edition_id` to `editions.id`.

The `juzs` and `hizbs` tables contain navigation ranges, but not every apparent
relationship is enforced as a foreign key. The source dump has a field named
`ayahs.hizb_id` that in fact spans 1–240 and holds rub-el-hizb quarter segments.
The converters rename it to `ayahs.rub_id` and constrain it with
`CHECK(rub_id BETWEEN 1 AND 240)`, so the enriched model no longer suggests a
join that would return wrong rows. Derive the hizb with
`FLOOR((rub_id - 1) / 4) + 1` when you need the 60-row lookup.
`ayahs.juz_id` spans 1–30 and does correspond to the `juzs` lookup.
`ayahs.page` spans 1–604; the converters derive the `pages` table directly
from that source field. The range endpoints describe the first and last ayah
assigned to each page, rather than attempting to model a visual page layout.

Range endpoints such as `start_ayah_id` and `end_ayah_id` are descriptive data.
Changes to these values should be validated against the source and should not
be inferred solely from table names.

## Import lifecycle

At a high level, each converter:

1. creates or recreates its target schema;
2. streams and parses supported `INSERT` statements from `quran.sql`;
3. loads `surahs`, `ayahs`, `editions`, and `ayah_edition`;
4. populates the `juzs`, `hizbs`, and `pages` lookup tables;
5. creates the convenience views;
6. prints row counts for inspection.

Changes to this lifecycle should preserve referential integrity and leave no
partially initialized database after a failed import. Import order matters
because the source dump does not necessarily list tables in foreign-key
dependency order.

### Tables not carried forward

The dump was taken from a Laravel application, so it also contains `users`,
`password_resets`, and `migrations`. Only `migrations` holds rows — the eight
migration filenames that built the schema in 2018. `users` and `password_resets`
are empty definitions; no account, email, or credential has ever been in this
repository.

Both converters load from an explicit allow-list (`TABLE_ORDER`), so the SQLite
and PostgreSQL targets never see these three tables. A direct `mysql < quran.sql`
import does create them, harmlessly; see the README for the one-line drop.

Widening `TABLE_ORDER` is how a table becomes part of the enriched model. It is
an allow-list on purpose: an unrecognised table in a future dump is skipped
rather than silently imported.

## Architectural boundaries

- The repository does not currently expose an application API.
- It does not currently manage user accounts, bookmarks, audio, search, or
  client applications.
- Translations are modeled as editions and per-ayah edition text; structured
  qira'at or riwayat transmission metadata is not yet modeled.
- Generated databases are delivery artifacts, not hand-edited sources.
- The Arabic text is checksum-verified in CI against
  `manifest/quran-arabic.manifest.json`; see [`provenance.md`](provenance.md).
  Translations carry no such guarantee — no checksum makes a translation correct.
- Changes to Quranic content require explicit provenance and review; see
  [`CONTRIBUTING.md`](../CONTRIBUTING.md).

Docker is a separate, verified layer around this conversion core: Compose builds
the source MySQL database and the enriched PostgreSQL and SQLite outputs from
the same tracked dump. API, search, and riwayat work remain future layers.
Planned components should remain clearly marked until their implementation and
verification are merged — as working files, not empty ones.
