FROM node:20-bookworm AS frontend

WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget ca-certificates \
    && wget -O /tmp/megacmd-Debian_12_amd64.deb https://mega.nz/linux/repo/Debian_12/amd64/megacmd-Debian_12_amd64.deb \
    && apt-get install -y --no-install-recommends /tmp/megacmd-Debian_12_amd64.deb \
    && rm -f /tmp/megacmd-Debian_12_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY recordtree ./recordtree
COPY --from=frontend /app/web/dist ./web/dist

RUN python -m pip install -e ".[web]"

RUN mkdir -p env downloads logs files/uploads

EXPOSE 7647

CMD ["uvicorn", "recordtree.web.api:app", "--host", "0.0.0.0", "--port", "7647"]
