# RecordTreeDownloader SQLite

RecordTreeDownloader SQLite is a local Python tool for importing Record Tree metadata into SQLite, searching it, and downloading selected MEGA links through MEGAcmd. It includes the original CLI and a Docker-ready WebUI backed by FastAPI and React.

The tool is intentionally local-first. It does not crawl remote sources or store MEGA credentials. MEGA authentication stays in your MEGAcmd installation.

## Docker WebUI

The recommended deployment path for the WebUI is Docker Compose. The production image builds the React frontend, serves it from the FastAPI backend, and installs the official Debian 12 MEGAcmd package inside the container.

Build and start the WebUI:

```bash
docker compose build
docker compose up -d
```

Open:

```text
http://127.0.0.1:8000
```

Initialize the runtime config and SQLite database:

```bash
docker compose exec recordtree-web recordtree init
```

Log in to MEGA through MEGAcmd inside the container, then verify the system:

```bash
docker compose exec recordtree-web mega-login
docker compose exec recordtree-web recordtree doctor
```

MEGA credentials are managed by MEGAcmd and are not stored by this application. The Compose file mounts a named Docker volume, `megacmd-home`, at `/root`; that volume stores MEGAcmd login state and survives container recreation unless you remove volumes with `docker compose down -v`.

Runtime data is mounted from the host so it survives container recreation:

- `./env:/app/env` for config and SQLite data
- `./downloads:/app/downloads` for downloaded files
- `./logs:/app/logs` for import error CSVs and logs
- `./files:/app/files` for uploaded/import source files

More Docker notes are in [Docker Development Guide](dev_documents_webui/docker_development.md).

## Installation

On Windows, the recommended setup is to run the installer script from the project root:

```bat
run-install.bat
```

The script uses an existing Python 3.11+ installation when available. If Python is not available, it downloads Python 3.12.10 into `env/python`. Project dependencies are installed into a root `.venv` directory, which lets VS Code automatically discover the interpreter when you open this folder. Runtime config and data remain under `env/`.

After setup, run the local CLI directly:

```powershell
.\.venv\Scripts\recordtree.exe doctor
```

For a lightweight developer setup when Python 3 is already installed:

```powershell
.\setup_env.ps1
```

MEGAcmd is still required for downloads.

## Initialize

Create the local config, SQLite database, download directory, and log directory:

```bash
recordtree init
```

Default generated paths:

- Config: `env/config.toml`
- Database: `env/recordtree.sqlite3`
- Downloads: `downloads/`
- Logs: `logs/`
- Import error CSVs: `logs/import_<import_id>_errors.csv`

Edit `env/config.toml` if you want custom paths, MEGAcmd executable names, or download safety margin settings.

## Import Data

Use the same command for the primary Excel workbook, legacy SQLite database, and legacy JSON export:

```bash
recordtree import "files/Record Tree 260605.xlsx"
recordtree import files/record.db
recordtree import "files/Record Tree.Json"
```

Recommended order is Excel first, then the legacy SQLite database, then the legacy JSON export. Excel is treated as the highest-quality metadata source; the legacy SQLite import then attaches old download history by matching existing active URLs, and JSON remains a lower-priority compatibility source.

Imports are designed to be repeatable. The importer upserts record groups by a generated source key and preserves historical inactive links when a record's active link set changes.

Before importing a large legacy database or doing a large re-import, back up `env/recordtree.sqlite3`. If SQLite WAL files exist, include `env/recordtree.sqlite3-wal` and `env/recordtree.sqlite3-shm`, or use the SQLite backup API.

## Search And Inspect

```bash
recordtree search-actor "<name>"
recordtree actor-records 12
recordtree search-source niconico
recordtree search-title ASMR
recordtree search-date --from 2026-01-01 --to 2026-01-31
recordtree list-undownloaded --limit 20
recordtree list-undownloaded --actor-id 12 --limit 20
recordtree info 123
recordtree stats
```

Search commands are case-insensitive and default to a limit of 50 rows. `search-actor` returns matching actors and their ids; use `actor-records <actor-id>` to list that actor's records.

## Download

Log in with MEGAcmd outside this tool first:

```bash
mega-login
```

Then check local readiness:

```bash
recordtree doctor
```

Download examples:

```bash
recordtree download 123 --types mp4,m4a
recordtree download 123 --include-par2 --yes
recordtree download 123 --output "D:/RecordTree/123"
recordtree download --actor 12 --count 5 --yes
```

By default, `.par2` files are excluded. Use `--include-par2` to include them. Actor downloads select up to three undownloaded records by default; use `--count` or `--limit` to choose another number. The downloader checks MEGAcmd availability, login status, selected byte count, and free disk space before running `mega-get`.

## Troubleshooting

Useful commands:

```bash
recordtree doctor
recordtree stats
recordtree info <id>
recordtree list-undownloaded --limit 20
recordtree list-undownloaded --actor-id <actor-id>
```

Common failures:

- Missing config or database: run `recordtree init`.
- Unsupported import extension: use `.xlsx`, `.xlsm`, `.json`, `.db`, `.sqlite`, or `.sqlite3`.
- Import row errors: check `logs/import_<import_id>_errors.csv`.
- MEGAcmd missing: install MEGAcmd and ensure `mega-get` and `mega-whoami` are on `PATH`, or configure executable paths in `env/config.toml`.
- Not logged in: run `mega-login` manually, then `recordtree doctor`.
- Insufficient disk space: change `--output`, free space, or adjust the safety margin in `env/config.toml`.

## Testing

Run the automated test suite:

```bash
pytest
```

MEGAcmd tests use mocks and do not require a real MEGA account or network access.

## Maintainer Docs

- [Architecture](documents/architecture.md)
- [Data contract](documents/data_contract.md)
- [Testing guide](documents/testing_guide.md)
