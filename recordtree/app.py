from __future__ import annotations

from pathlib import Path

from . import config as config_module
from . import db
from .exceptions import NotImplementedFeatureError
from .models import InitResult


class RecordTreeApp:
    """Application service layer for CLI use cases."""

    def init(self) -> InitResult:
        config_path = config_module.ensure_config(Path("env/config.toml"))
        app_config = config_module.load_config(config_path)

        app_config.database_path.parent.mkdir(parents=True, exist_ok=True)
        app_config.downloads_dir.mkdir(parents=True, exist_ok=True)
        app_config.logs_dir.mkdir(parents=True, exist_ok=True)

        conn = db.connect(app_config.database_path)
        try:
            db.initialize_schema(conn)
            schema_version = conn.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'"
            ).fetchone()
        finally:
            conn.close()

        return InitResult(
            config_path=config_path,
            database_path=app_config.database_path,
            downloads_dir=app_config.downloads_dir,
            logs_dir=app_config.logs_dir,
            schema_version=schema_version["value"] if schema_version else "unknown",
        )

    def doctor(self) -> None:
        raise NotImplementedFeatureError("Doctor checks are not implemented yet.")

    def import_file(self, path: Path) -> None:
        raise NotImplementedFeatureError(f"Import is not implemented yet: {path}")

    def stats(self) -> None:
        raise NotImplementedFeatureError("Stats are not implemented yet.")
