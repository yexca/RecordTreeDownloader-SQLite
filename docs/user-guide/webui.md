# WebUI Guide

The WebUI provides a browser interface for the same local workflows as the CLI.

## Start With Docker

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

## Main Areas

- Dashboard: database totals, recent imports, recent downloads, and download status buckets.
- Search: actor, title, source, date range, and undownloaded records.
- Record detail: metadata, active links, link status, and download planning.
- Import: upload Excel, legacy JSON, or legacy SQLite files and track background progress.
- Maintenance: configuration, database backups, writable paths, MEGAcmd availability, and integrity checks.

## Downloads

The WebUI builds a download plan before starting MEGAcmd. You can choose:

- Whether to include `.par2`
- File type filters such as `mp4,m4a`
- Output directory
- Only undownloaded links

Downloads run as background jobs. The UI polls job status and displays captured MEGAcmd output for active jobs. Completed download details also expose persisted MEGAcmd output when a log file is available.

Download output logs are written under:

```text
logs/downloads/download_<download_id>.log
```
