# Quran Database

A comprehensive MySQL and SQLite database containing the complete Quran text with multiple translations and editions.

## Contents

| File | Format | Size | Description |
| ---- | ------ | ---- | ----------- |
| `quran.sql.zip` | MySQL dump | ~187 MB uncompressed | Full database dump for MySQL |
| `quran.db.gz` | SQLite database | ~208 MB uncompressed | Full database for SQLite |
| `convert_to_sqlite.py` | Python script | — | Converts `quran.sql` to `quran.db` |

## Database Schema

The actual schema (dynamically extracted from the MySQL dump):

### `surahs`

Stores metadata for all 114 surahs.

| Column | Description |
| --- | --- |
| `id` | Surah number |
| `number` | Surah number |
| `name_ar` | Surah name in Arabic (e.g. الفاتحة) |
| `name_en` | Surah name transliterated (e.g. Al-Fatiha) |
| `name_en_translation` | English meaning (e.g. The Opening) |
| `type` | Revelation type (Meccan / Medinan) |

### `ayahs`

Contains the original Arabic text of every ayah (6,236 verses).

| Column | Description |
| --- | --- |
| `id` | Unique ayah ID (1–6236) |
| `number` | Global ayah number |
| `text` | Ayah text in Arabic |
| `number_in_surah` | Ayah number within its surah |
| `page` | Mushaf page number |
| `surah_id` | Reference to surah |
| `hizb_id` | Reference to hizb (1–60) |
| `juz_id` | Reference to juz (1–30) |
| `sajda` | Prostration marker (0/1) — 15 ayahs |

### `editions`

Available translations and editions (134 entries).

| Column | Description |
| --- | --- |
| `id` | Unique ID |
| `identifier` | Unique identifier (e.g. `en.sahih`) |
| `language` | Language code |
| `name` | Edition name in native language |
| `english_name` | Edition name in English |
| `format` | Format (`text`) |
| `type` | Type (`translation`, `tafsir`) |

### `ayah_edition`

Ayah-by-ayah translations (835,624 rows — 6,236 ayahs × 134 editions).

| Column | Description |
| --- | --- |
| `id` | Unique ID |
| `ayah_id` | Reference to ayah |
| `edition_id` | Reference to edition |
| `data` | Translated/annotated text |
| `is_audio` | Audio flag |

### `juzs` (SQLite only — new)

30 juz (parts) with ayah ranges.

| Column | Description |
| --- | --- |
| `id` | Juz ID (1–30) |
| `juz_number` | Juz number |
| `name_ar` | Arabic name (e.g. الجزء الأول) |
| `start_ayah_id` | First ayah in this juz |
| `end_ayah_id` | Last ayah in this juz |

### `hizbs` (SQLite only — new)

60 hizbs (half-parts) with ayah ranges and juz references.

| Column | Description |
| --- | --- |
| `id` | Hizb ID (1–60) |
| `hizb_number` | Hizb number |
| `juz_id` | Parent juz |
| `name_ar` | Arabic name |
| `start_ayah_id` | First ayah in this hizb |
| `end_ayah_id` | Last ayah in this hizb |

## Setup

### Web reader

The dependency-free reader in `docs/` displays the complete Arabic Quran using
the database's 604-page mapping. It includes Uthmani and locally hosted
Indo-Pak Nastaleeq display modes. Start it locally with PHP:

```bash
php -S localhost:8000 -t docs
```

Then visit <http://localhost:8000>. Regenerate its compact JSON data directly
from the bundled SQLite archive and run its checks with:

```bash
python3 scripts/export_web_data.py
python3 scripts/download_nastaleeq.py
python3 scripts/import_nastaleeq.py
python3 -m unittest discover -s tests -v
```

The Nastaleeq font and matching script provenance are documented in
`docs/fonts/README.md` and `docs/data/README.md`. The alternate script is kept
separate and never rewrites the source database.

The deployment workflow publishes `docs/` to GitHub Pages after changes reach
`main`. Repository maintainers must select **GitHub Actions** as the Pages source
once under **Settings → Pages**.

### MySQL

1. Extract the SQL file:
   ```bash
   unzip quran.sql.zip
   ```

2. Import into MySQL:
   ```bash
   mysql -u <username> -p <database_name> < quran.sql
   ```

### SQLite

1. Extract the database:
   ```bash
   gunzip quran.db.gz
   ```

2. Open with any SQLite client:
   ```bash
   sqlite3 quran.db
   ```

   Or use in Python:
   ```python
   import sqlite3
   db = sqlite3.connect("quran.db")
   # Get Surah Al-Fatiha
   rows = db.execute("SELECT * FROM ayahs WHERE surah_id = 1").fetchall()
   # Get ayah with translation
   rows = db.execute("SELECT arabic, translation FROM ayah_with_translation WHERE surah_id = 1 AND language = 'en'").fetchall()
   ```

3. To regenerate from the MySQL dump:
   ```bash
   unzip quran.sql.zip
   python3 convert_to_sqlite.py
   ```

The SQLite version adds:
- Proper **foreign key constraints** and **CHECK constraints**
- **Indexes** on commonly queried columns (surah_id, juz_id, hizb_id, page, number_in_surah, sajda)
- Pre-populated **`juzs`** and **`hizbs`** lookup tables with ayah ranges
- Views: `surah_stats` (ayat counts per surah), `ayah_with_translation` (joined ayah + translation)

## Roadmap

We welcome contributions! Here's the planned roadmap for this project. Pick any item and submit a PR.

### Database Improvements
- [x] Add proper indexes for faster queries
- [x] Add `juz` (parts) table with ayah ranges
- [x] Add `hizb` and `rub` (quarter) divisions
- [ ] Add `pages` table (Mushaf page mapping)
- [ ] Add word-by-word breakdown table (Arabic root, morphology)
- [x] Add sajdah (prostration) markers
- [x] Support ~~PostgreSQL and~~ SQLite exports
- [x] Add foreign key constraints and proper normalization

### Data Expansion
- [ ] Add more translations (Urdu, French, Turkish, Indonesian, etc.)
- [ ] Add Tafsir (exegesis) data — Ibn Kathir, Al-Tabari, Al-Sa'di, etc.
- [ ] Add audio recitation references (Mishary, Al-Husary, Abdul Basit, etc.)
- [ ] Add transliteration for each ayah
- [ ] Add asbab al-nuzul (reasons of revelation)
- [ ] Add hadith references related to each ayah
- [ ] Add dua (supplication) extractions from the Quran

### API / Backend
- [ ] Build a RESTful API (Node.js or Python)
- [ ] GraphQL endpoint for flexible queries
- [ ] Search endpoint with full-text Arabic search
- [ ] Pagination and filtering support
- [ ] API rate limiting and authentication
- [ ] Docker setup for easy deployment
- [ ] API documentation (Swagger / OpenAPI)

### Frontend / App
- [ ] Web app for browsing surahs and ayahs
- [ ] Ayah-by-ayah reader with translation toggle
- [ ] Audio player integration with reciter selection
- [ ] Search functionality (by surah, ayah, keyword)
- [ ] Bookmarking and progress tracking
- [ ] Dark mode and responsive design
- [ ] Mobile-friendly PWA support

## Contributing

Contributions are welcome and encouraged! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Commit** your changes: `git commit -m "Add your feature"`
4. **Push** to the branch: `git push origin feature/your-feature`
5. **Open** a Pull Request

### Contribution Guidelines
- Follow the existing database schema conventions
- Include sample queries or screenshots for database changes
- Add tests for API endpoints
- Keep translations accurate — reference established scholarly sources
- For new data, include the source/reference

If you're unsure where to start, look for items marked in the roadmap above or open an issue to discuss your idea.

## Screenshots

![Surahs Table](screenshots/Screen%20Shot%202022-04-19%20at%207.56.15%20AM.png)
![Ayahs Table](screenshots/Screen%20Shot%202022-04-19%20at%207.55.54%20AM.png)
![Editions Table](screenshots/Screen%20Shot%202022-04-19%20at%207.56.08%20AM.png)
![Addons Table](screenshots/Screen%20Shot%202022-04-19%20at%207.55.32%20AM.png)

## Related Projects

- [Quran Lumen API](https://github.com/AbdullahGhanem/quran-lumen-api) — Laravel Lumen API
- [Quran Vue](https://github.com/adibemohamed/quranaho)

## Sponsor

[Become a Sponsor](https://github.com/sponsors/AbdullahGhanem)

## License

This project is open source. The Quran text is in the public domain.
