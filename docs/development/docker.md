# Docker WebUI Runtime Guide

This guide covers the production-style Docker WebUI container defined by `Dockerfile` and `docker-compose.yml`. It builds the React frontend, serves the built assets from FastAPI, and installs the official Debian 12 MEGAcmd package so download workflows use the same `mega-*` commands expected by the CLI.

For the bind-mounted development/test container, use [Development test container](test-container.md) instead.

## Build And Start

```bash
docker compose build
docker compose up -d
```

Open the WebUI at:

```text
http://127.0.0.1:7647
```

## Initialize Runtime Data

```bash
docker compose exec recordtree-web recordtree init
docker compose exec recordtree-web recordtree doctor
```

## MEGA Login

MEGA credentials are managed by MEGAcmd, not by RecordTreeDownloader SQLite. Log in from the WebUI Settings page or inside the container with:

```bash
docker compose exec recordtree-web mega-login
docker compose exec recordtree-web recordtree doctor
```

The host directory `./env/megacmd-home` is mounted at `/root` and stores MEGAcmd login state. Recreating the container keeps this login state as long as that directory is not removed.

## Persistent Data

The compose file mounts these host directories into the container:

- `./env:/app/env` for config and SQLite database
- `./downloads:/app/downloads` for downloaded files
- `./logs:/app/logs` for import error CSVs, backups, and download logs such as `logs/downloads/download_<download_id>.log`
- `./files:/app/files` for uploaded import files

Runtime data survives container recreation because these paths live on the host. The MEGAcmd login state survives through `./env/megacmd-home`.

## Useful Commands

```bash
docker compose logs -f recordtree-web
docker compose exec recordtree-web recordtree stats
docker compose exec recordtree-web recordtree import /app/files/example.json
docker compose down
```
