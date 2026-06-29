# RecordTreeDownloader SQLite

RecordTreeDownloader SQLite is a local-first tool for importing Record Tree metadata into SQLite, searching it, and downloading selected MEGA links through MEGAcmd. It provides both a CLI and a Docker-ready WebUI backed by FastAPI and React.

The application does not crawl remote sources and does not store MEGA credentials. MEGA authentication stays in your MEGAcmd installation.

## Features

- Import Excel workbooks, legacy SQLite databases, and legacy JSON exports.
- Search records by actor, title, source, date range, and download status.
- Inspect record groups and active MEGA links.
- Download selected links through MEGAcmd with disk-space checks.
- Use either the CLI or the WebUI.
- Keep runtime data local in SQLite and local folders.

## Quick Start

### Docker WebUI

```bash
docker compose build
docker compose up -d
docker compose exec recordtree-web recordtree init
docker compose exec recordtree-web mega-login
docker compose exec recordtree-web recordtree doctor
```

Open:

```text
http://127.0.0.1:8000
```

### CLI

On Windows, run:

```bat
run-install.bat
```

Then initialize and check the environment:

```powershell
.\.venv\Scripts\recordtree.exe init
.\.venv\Scripts\recordtree.exe doctor
```

## Documentation

- [Documentation index](docs/README.md)
- [CLI guide](docs/user-guide/cli.md)
- [WebUI guide](docs/user-guide/webui.md)
- [Docker deployment](docs/user-guide/docker.md)
- [Troubleshooting](docs/user-guide/troubleshooting.md)
- [Architecture](docs/maintainer-guide/architecture.md)
- [Data contract](docs/maintainer-guide/data-contract.md)
- [Testing guide](docs/maintainer-guide/testing.md)

## Safety Notes

- Do not commit real exports, downloaded files, MEGA credentials, or runtime databases.
- Keep sensitive manual-test data under `real_test/`; that path is ignored by Git.
- In Docker, MEGAcmd login state is stored in the `megacmd-home` named volume.

## Development

Install local development dependencies:

```bash
python -m pip install -e ".[web,dev]"
pytest
```

Build the frontend:

```bash
cd web
npm install
npm run build
```
