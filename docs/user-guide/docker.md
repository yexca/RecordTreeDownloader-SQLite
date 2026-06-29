# Docker Deployment

The production Docker image builds the React frontend, serves it from the FastAPI backend, and installs the official Debian 12 MEGAcmd package.

## Build And Start

```bash
docker compose build
docker compose up -d
```

Open:

```text
http://127.0.0.1:8000
```

## Initialize Runtime Data

```bash
docker compose exec recordtree-web recordtree init
docker compose exec recordtree-web recordtree doctor
```

## MEGA Login

MEGA credentials are managed by MEGAcmd, not by RecordTreeDownloader SQLite.

```bash
docker compose exec recordtree-web mega-login
docker compose exec recordtree-web recordtree doctor
```

The `megacmd-home` Docker named volume is mounted at `/root` and stores MEGAcmd login state.

## Persistent Data

The Compose file mounts these host directories:

- `./env:/app/env`
- `./downloads:/app/downloads`
- `./logs:/app/logs`
- `./files:/app/files`

Runtime data survives container recreation because these paths live on the host. MEGAcmd login state survives through the `megacmd-home` named volume.

## Useful Commands

```bash
docker compose logs -f recordtree-web
docker compose exec recordtree-web recordtree stats
docker compose exec recordtree-web recordtree import /app/files/example.json
docker compose down
docker compose down -v
```

Use `docker compose down -v` only when you intentionally want to delete the MEGAcmd login volume.
