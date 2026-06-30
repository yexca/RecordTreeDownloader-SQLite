# Development Test Container

Use this container when you want one Linux environment with both Python development dependencies and Node dependencies installed. It is separate from the production-style `docker-compose.yml` container.

## What It Includes

- Node 20 and npm dependencies from `web/package-lock.json`
- Python dev and WebUI dependencies from `pyproject.toml`
- The official Debian 12 MEGAcmd package
- A source bind mount so local edits are visible inside the container
- A named volume for `/workspace/web/node_modules`
- A host bind mount from `./env/megacmd-home-dev` to `/root`, which preserves MEGAcmd login state

## Build

```bash
docker compose -f docker-compose.dev.yml build
```

## Start

```bash
docker compose -f docker-compose.dev.yml up -d
```

The container stays running with `sleep infinity` so you can execute test and development commands inside it.

## Run Tests And Builds

```bash
docker compose -f docker-compose.dev.yml exec recordtree-dev pytest
docker compose -f docker-compose.dev.yml exec recordtree-dev sh -c "cd web && npm run build"
```

## Run Backend And Frontend Dev Servers

Open two shells:

```bash
docker compose -f docker-compose.dev.yml exec recordtree-dev uvicorn recordtree.web.api:app --host 0.0.0.0 --port 7647 --reload
```

```bash
docker compose -f docker-compose.dev.yml exec recordtree-dev sh -c "cd web && npm run dev -- --host 0.0.0.0"
```

Then open:

```text
http://127.0.0.1:5173
```

The Vite dev server proxies `/api` requests to the backend inside the same container.

## Initialize Runtime Data

```bash
docker compose -f docker-compose.dev.yml exec recordtree-dev recordtree init
docker compose -f docker-compose.dev.yml exec recordtree-dev recordtree doctor
```

`recordtree doctor` should find `mega-whoami` and `mega-get`. MEGA login remains owned by MEGAcmd:

```bash
docker compose -f docker-compose.dev.yml exec recordtree-dev mega-login
```

## Notes

Because the project root is bind-mounted into `/workspace`, Python source changes are visible immediately. If Python dependencies change, rebuild the image. If Node dependencies change, rebuild the image or run `npm ci` inside the container.

Stop the container with:

```bash
docker compose -f docker-compose.dev.yml down
```

Use `docker compose -f docker-compose.dev.yml down -v` only when you intentionally want to delete the Node dependency volume. MEGAcmd login state is stored in the host directory `./env/megacmd-home-dev`; remove that directory only when you intentionally want to reset the dev-container MEGAcmd session.
