set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# Show the available project commands.
default:
    @just --list

# Check that the local tools used by the current workflows are installed.
doctor:
    @command -v python3 >/dev/null
    @command -v unzip >/dev/null
    @echo "Required tools are available."

# Extract quran.sql from the repository's source archive when needed.
extract: doctor
    @if [[ -f quran.sql ]]; then \
        echo "quran.sql already exists; leaving it unchanged."; \
    else \
        unzip data/quran.sql.zip quran.sql; \
    fi

# Build quran.db from the MySQL dump.
sqlite: extract
    python3 convert_to_sqlite.py

# Build a PostgreSQL database from the MySQL dump. Honours PGHOST/PGUSER/PGDATABASE.
postgres: extract
    python3 convert_to_postgres.py

# Regenerate the readable schema references under schema/.
schema:
    python3 scripts/export_schema.py

# Check the Arabic text in quran.db against the shipped SHA-256 manifest.
verify:
    python3 scripts/checksum_text.py

# Rebuild the manifest after an intentional, sourced text change.
manifest:
    python3 scripts/checksum_text.py --generate

# Validate the Python converters and run the test suite.
check: doctor
    unzip -tqq data/quran.sql.zip
    python3 -c 'from pathlib import Path; [compile(Path(p).read_bytes(), p, "exec") for p in ("convert_to_sqlite.py", "convert_to_postgres.py", "scripts/checksum_text.py", "scripts/export_schema.py", "scripts/export_rukus.py", "scripts/export_web_data.py")]'
    python3 -m unittest discover -s tests

# Check that Docker and Docker Compose are available.
docker-doctor:
    @command -v docker >/dev/null
    @docker compose version >/dev/null
    @echo "Docker and Docker Compose are available."

# Validate the Compose model and database initialization scripts.
docker-check: docker-doctor
    docker compose config --quiet
    bash -n docker/mysql/install.sh docker/postgres/install.sh docker/sqlite/install.sh

# Build all database images.
docker-build: docker-doctor
    docker compose build

# Start MySQL and PostgreSQL and generate output/quran.db.
docker-up: docker-doctor
    LOCAL_UID="$$(id -u)" LOCAL_GID="$$(id -g)" docker compose up --build --detach

# Follow logs from all database services.
docker-logs: docker-doctor
    docker compose logs --follow

# Generate only output/quran.db in a temporary container.
docker-sqlite: docker-doctor
    LOCAL_UID="$$(id -u)" LOCAL_GID="$$(id -g)" docker compose run --build --rm sqlite

# Stop the Docker services while preserving database volumes.
docker-down: docker-doctor
    docker compose down
