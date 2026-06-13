from __future__ import annotations

import csv
from pathlib import Path

from . import config as config_module
from . import db
from .exceptions import ImportRowError, NotFoundError, NotImplementedFeatureError, ValidationError
from .importer.excel import ExcelImporter
from .importer.service import ImportService, apply_upsert_result
from .models import ImportResult, ImportStats, InitResult
from .repositories import ImportRepository


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

    def import_file(self, path: Path) -> ImportResult:
        source_path = path.expanduser().resolve()
        if not source_path.exists():
            raise NotFoundError(f"Import source does not exist: {source_path}")
        source_type, importer = self._create_importer(source_path)

        config_path = config_module.ensure_config(Path("env/config.toml"))
        app_config = config_module.load_config(config_path)
        app_config.database_path.parent.mkdir(parents=True, exist_ok=True)
        app_config.logs_dir.mkdir(parents=True, exist_ok=True)

        conn = db.connect(app_config.database_path)
        db.initialize_schema(conn)
        import_repo = ImportRepository(conn)
        import_id = import_repo.create_import(source_type, source_path)
        stats = ImportStats()
        error_csv_path: Path | None = None
        status = "completed"
        try:
            with db.transaction(conn):
                service = ImportService(conn)
                for record in importer.iter_records(source_path):
                    stats.total_rows += 1
                    if isinstance(record, ImportRowError):
                        service.record_error(import_id, record)
                        stats.error_count += 1
                        continue
                    try:
                        result = service.upsert_record(import_id, record)
                    except ImportRowError as error:
                        service.record_error(import_id, error)
                        stats.error_count += 1
                    else:
                        apply_upsert_result(stats, result)
                status = "completed_with_errors" if stats.error_count else "completed"
                import_repo.finish_import(
                    import_id,
                    stats,
                    status,
                    notes=_extra_columns_note(getattr(importer, "extra_columns", ())),
                )
            if stats.error_count:
                error_csv_path = _export_import_errors(conn, import_id, app_config.logs_dir)
        except Exception as error:
            import_repo.fail_import(import_id, str(error))
            conn.commit()
            raise
        finally:
            conn.close()

        return ImportResult(
            import_id=import_id,
            source_type=source_type,
            source_path=source_path,
            status=status,
            stats=stats,
            error_csv_path=error_csv_path,
            extra_columns=tuple(getattr(importer, "extra_columns", ())),
        )

    def stats(self) -> None:
        raise NotImplementedFeatureError("Stats are not implemented yet.")

    def _create_importer(self, path: Path):
        extension = path.suffix.casefold()
        if extension in {".xlsx", ".xlsm"}:
            return "xlsx", ExcelImporter()
        raise ValidationError(f"Unsupported import file extension: {extension}")


def _extra_columns_note(extra_columns: tuple[str, ...]) -> str | None:
    if not extra_columns:
        return None
    return "Extra Excel columns ignored: " + ", ".join(extra_columns)


def _export_import_errors(conn, import_id: int, logs_dir: Path) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / f"import_{import_id}_errors.csv"
    rows = ImportRepository(conn).list_errors(import_id)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "import_id",
                "row_number",
                "source_key",
                "error_type",
                "message",
                "raw_value",
                "created_at",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["import_id"],
                    row["row_number"],
                    row["source_key"],
                    row["error_type"],
                    row["message"],
                    row["raw_value"],
                    row["created_at"],
                ]
            )
    return path
