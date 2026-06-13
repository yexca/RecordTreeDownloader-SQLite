from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    downloads_dir: Path
    logs_dir: Path
    safety_margin_percent: int
    safety_margin_min_mb: int
    include_par2_by_default: bool
    mega_get: str
    mega_whoami: str
    prefer_xlsx_metadata: bool


def default_config() -> dict[str, object]:
    return {
        "paths": {
            "database": "env/recordtree.sqlite3",
            "downloads": "downloads",
            "logs": "logs",
        },
        "download": {
            "safety_margin_percent": 5,
            "safety_margin_min_mb": 512,
            "include_par2_by_default": False,
        },
        "mega": {
            "mega_get": "mega-get",
            "mega_whoami": "mega-whoami",
        },
        "import": {
            "prefer_xlsx_metadata": True,
        },
    }


def ensure_config(path: Path) -> Path:
    raise NotImplementedError


def load_config(path: Path | None = None) -> AppConfig:
    raise NotImplementedError


def resolve_path(base_dir: Path, configured_path: str) -> Path:
    candidate = Path(configured_path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()
