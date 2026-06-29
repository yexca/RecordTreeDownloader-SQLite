# Docker Development Guide

This project can run the FastAPI backend and built React WebUI from one Docker container. The image also installs the official Debian 12 MEGAcmd package so download workflows use the same `mega-*` commands expected by the CLI.

## Build And Start

```bash
docker compose build
docker compose up -d
```

Open the WebUI at:

```text
http://127.0.0.1:8000
```

## Initialize Runtime Data

```bash
docker compose exec recordtree-web recordtree init
docker compose exec recordtree-web recordtree doctor
```

## MEGA Login

MEGA credentials are managed by MEGAcmd, not by RecordTreeDownloader SQLite. Log in inside the container with:

```bash
docker compose exec recordtree-web mega-login
docker compose exec recordtree-web recordtree doctor
```

The `megacmd-home` Docker named volume is mounted at `/root` and stores MEGAcmd login state. Recreating the container keeps this login state as long as the named volume is not removed.

## Persistent Data

The compose file mounts these host directories into the container:

- `./env:/app/env` for config and SQLite database
- `./downloads:/app/downloads` for downloaded files
- `./logs:/app/logs` for import error CSVs and logs
- `./files:/app/files` for uploaded import files

Runtime data survives container recreation because these paths live on the host. The MEGAcmd login state survives through the `megacmd-home` named volume.

## Useful Commands

```bash
docker compose logs -f recordtree-web
docker compose exec recordtree-web recordtree stats
docker compose exec recordtree-web recordtree import /app/files/example.json
docker compose down
docker compose down -v
```

Use `docker compose down -v` only when you intentionally want to delete the MEGAcmd login volume.
