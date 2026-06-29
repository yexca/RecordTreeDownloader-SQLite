from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import replace
import os
from pathlib import Path

from . import config as config_module
from . import db
from . import mega
from .exceptions import ConfigError, ExternalToolError, ImportRowError, NotFoundError, NotImplementedFeatureError, ValidationError
from .importer.excel import ExcelImporter
from .importer.json_importer import JsonImporter
from .importer.legacy_db import LegacyDbImporter, LegacyMigrationService
from .importer.service import ImportService, apply_upsert_result
from .models import (
    ActorSummary,
    ActorDownloadResult,
    DoctorCheck,
    DoctorResult,
    DownloadExecutionResult,
    DownloadItemDetail,
    DownloadPage,
    DownloadPlan,
    ImportResult,
    ImportErrorPage,
    ImportPage,
    ImportProgress,
    ImportStats,
    LinkItem,
    InitResult,
    MegaCommandResult,
    MegaCommandStatus,
    MegaAccountStatus,
    RecordPage,
    RecordDetail,
    RecordSummary,
    SourceSummary,
    StatsResult,
)
from .normalizers import build_source_key, clean_text, normalize_file_type
from .repositories import DownloadRepository, ImportRepository
from .search import SearchService, normalize_limit, normalize_page


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
        checks: list[DoctorCheck] = []
        config_path = Path("env/config.toml").expanduser()
        app_config = None
        if config_path.exists():
            try:
                app_config = config_module.load_config(config_path)
            except ConfigError as error:
                checks.append(DoctorCheck("config", "fail", str(error)))
            else:
                checks.append(DoctorCheck("config", "pass", str(config_path.resolve())))
        else:
            checks.append(DoctorCheck("config", "fail", f"Config file does not exist: {config_path}"))

        if app_config is not None:
            try:
                conn = db.connect(app_config.database_path)
                try:
                    version = conn.execute(
                        "SELECT value FROM schema_meta WHERE key = 'schema_version'"
                    ).fetchone()
                finally:
                    conn.close()
            except Exception as error:
                checks.append(DoctorCheck("database", "fail", str(error)))
                checks.append(DoctorCheck("schema", "fail", "Schema version could not be read."))
            else:
                checks.append(DoctorCheck("database", "pass", str(app_config.database_path)))
                if version is None:
                    checks.append(DoctorCheck("schema", "fail", "schema_version is missing."))
                else:
                    checks.append(DoctorCheck("schema", "pass", str(version["value"])))

            for name, path in (("downloads_dir", app_config.downloads_dir), ("logs_dir", app_config.logs_dir)):
                checks.append(_check_writable_dir(name, path))

            whoami = _check_executable("mega-whoami", app_config.mega_whoami)
            get = _check_executable("mega-get", app_config.mega_get)
            checks.extend([whoami[0], get[0]])
            if whoami[1] is not None:
                login = mega.check_login(whoami[1])
                if login.logged_in:
                    checks.append(DoctorCheck("mega_login", "pass", login.message))
                else:
                    checks.append(
                        DoctorCheck(
                            "mega_login",
                            "fail",
                            "MEGA is not logged in. Use Settings or run mega-login.",
                        )
                    )
            else:
                checks.append(DoctorCheck("mega_login", "warn", "Skipped because mega-whoami is unavailable."))

        return DoctorResult(checks)

    def mega_status(self) -> MegaAccountStatus:
        config_path = config_module.ensure_config(Path("env/config.toml"))
        app_config = config_module.load_config(config_path)
        get_status = _mega_command_status(app_config.mega_get)
        whoami_status = _mega_command_status(app_config.mega_whoami)
        login_status = _mega_command_status(app_config.mega_login)
        logout_status = _mega_command_status(app_config.mega_logout)
        if whoami_status.resolved is None:
            login = MegaLoginStatus(False, 1, "Skipped because mega-whoami is unavailable.")
        else:
            login = mega.check_login(whoami_status.resolved)
        return MegaAccountStatus(
            login=login,
            mega_get=get_status,
            mega_whoami=whoami_status,
            mega_login=login_status,
            mega_logout=logout_status,
            home_dir=Path.home(),
            persistence_dir=_megacmd_persistence_dir(),
        )

    def mega_login(
        self,
        email: str,
        password: str,
        auth_code: str | None = None,
    ) -> MegaAccountStatus:
        clean_email = email.strip()
        if not clean_email:
            raise ValidationError("MEGA email is required.")
        if not password:
            raise ValidationError("MEGA password is required.")
        config_path = config_module.ensure_config(Path("env/config.toml"))
        app_config = config_module.load_config(config_path)
        mega_login = mega.resolve_executable(app_config.mega_login)
        result = mega.login_account(mega_login, clean_email, password, auth_code.strip() if auth_code else None)
        if result.exit_code != 0:
            message = _command_message(result.stdout, result.stderr) or f"mega-login failed with exit code {result.exit_code}."
            raise ExternalToolError(message.replace(password, "<redacted>"))
        return self.mega_status()

    def mega_logout(self) -> MegaAccountStatus:
        config_path = config_module.ensure_config(Path("env/config.toml"))
        app_config = config_module.load_config(config_path)
        mega_logout = mega.resolve_executable(app_config.mega_logout)
        result = mega.logout_account(mega_logout)
        if result.exit_code != 0:
            message = _command_message(result.stdout, result.stderr) or f"mega-logout failed with exit code {result.exit_code}."
            raise ExternalToolError(message)
        return self.mega_status()

    def import_file(
        self,
        path: Path,
        progress_callback: Callable[[ImportProgress], None] | None = None,
    ) -> ImportResult:
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
        notes: str | None = None
        try:
            total_rows = _count_import_rows(importer, source_path)
            _report_import_progress(progress_callback, source_type, source_path, 0, total_rows, "Importing")
            with db.transaction(conn):
                service = ImportService(conn, prefer_xlsx_metadata=app_config.prefer_xlsx_metadata)
                if isinstance(importer, LegacyDbImporter):
                    migration = LegacyMigrationService(conn, import_id)
                    for legacy_row in importer.iter_rows(source_path):
                        stats.total_rows += 1
                        migration.migrate_row(legacy_row, stats)
                        _report_import_progress(
                            progress_callback,
                            source_type,
                            source_path,
                            stats.total_rows,
                            total_rows,
                            "Importing",
                        )
                elif isinstance(importer, ExcelImporter):
                    _import_excel_records(
                        importer,
                        source_path,
                        service,
                        import_id,
                        stats,
                        progress_callback,
                        total_rows,
                        source_type,
                    )
                else:
                    for record in importer.iter_records(source_path):
                        stats.total_rows += 1
                        if isinstance(record, ImportRowError):
                            service.record_error(import_id, record)
                            stats.error_count += 1
                        else:
                            try:
                                result = service.upsert_record(import_id, record)
                            except ImportRowError as error:
                                service.record_error(import_id, error)
                                stats.error_count += 1
                            else:
                                apply_upsert_result(stats, result)
                        _report_import_progress(
                            progress_callback,
                            source_type,
                            source_path,
                            stats.total_rows,
                            total_rows,
                            "Importing",
                        )
                status = "completed_with_errors" if stats.error_count else "completed"
                notes = _import_notes(importer)
                import_repo.finish_import(
                    import_id,
                    stats,
                    status,
                    notes=notes,
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
            notes=notes,
        )

    def list_imports(
        self,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        source_type: str | None = None,
    ) -> ImportPage:
        normalized_page = normalize_page(page)
        normalized_page_size = normalize_limit(page_size)
        conn = self._open_app_db()
        try:
            repo = ImportRepository(conn)
            total = repo.count_imports(status=status, source_type=source_type)
            offset = (normalized_page - 1) * normalized_page_size
            items = repo.list_imports(
                normalized_page_size,
                offset,
                status=status,
                source_type=source_type,
            )
            total_pages = (total + normalized_page_size - 1) // normalized_page_size if total else 0
            return ImportPage(items=items, page=normalized_page, page_size=normalized_page_size, total=total, total_pages=total_pages)
        finally:
            conn.close()

    def get_import(self, import_id: int):
        if import_id < 1:
            raise ValidationError("Import id must be at least 1.")
        conn = self._open_app_db()
        try:
            result = ImportRepository(conn).get_import(import_id)
            if result is None:
                raise NotFoundError(f"Import not found: {import_id}")
            return result
        finally:
            conn.close()

    def list_import_errors(self, import_id: int, page: int = 1, page_size: int = 100) -> ImportErrorPage:
        if import_id < 1:
            raise ValidationError("Import id must be at least 1.")
        normalized_page = normalize_page(page)
        normalized_page_size = normalize_limit(page_size)
        conn = self._open_app_db()
        try:
            repo = ImportRepository(conn)
            if repo.get_import(import_id) is None:
                raise NotFoundError(f"Import not found: {import_id}")
            total = repo.count_errors(import_id)
            offset = (normalized_page - 1) * normalized_page_size
            items = repo.list_error_details(import_id, normalized_page_size, offset)
            total_pages = (total + normalized_page_size - 1) // normalized_page_size if total else 0
            return ImportErrorPage(items=items, page=normalized_page, page_size=normalized_page_size, total=total, total_pages=total_pages)
        finally:
            conn.close()

    def stats(self) -> StatsResult:
        conn = self._open_app_db()
        try:
            return SearchService(conn).stats()
        finally:
            conn.close()

    def search_actor(self, name: str, limit: int = 50) -> list[ActorSummary]:
        conn = self._open_app_db()
        try:
            return SearchService(conn).search_actor(name, limit)
        finally:
            conn.close()

    def get_actor(self, actor_id: int) -> ActorSummary:
        conn = self._open_app_db()
        try:
            return SearchService(conn).get_actor(actor_id)
        finally:
            conn.close()

    def list_actor_records(self, actor_id: int, limit: int = 50) -> list[RecordSummary]:
        conn = self._open_app_db()
        try:
            return SearchService(conn).list_actor_records(actor_id, limit)
        finally:
            conn.close()

    def search_platform(self, name: str, limit: int = 50) -> list[SourceSummary]:
        conn = self._open_app_db()
        try:
            return SearchService(conn).search_platform(name, limit)
        finally:
            conn.close()

    def get_platform(self, source_id: int) -> SourceSummary:
        conn = self._open_app_db()
        try:
            return SearchService(conn).get_platform(source_id)
        finally:
            conn.close()

    def list_platform_records(self, source_id: int, limit: int = 50) -> list[RecordSummary]:
        conn = self._open_app_db()
        try:
            return SearchService(conn).list_platform_records(source_id, limit)
        finally:
            conn.close()

    def list_records(
        self,
        *,
        record_id: int | None = None,
        title: str = "",
        actor: str = "",
        source: str = "",
        date_from: str | None = None,
        date_to: str | None = None,
        downloaded: str | None = None,
        file_type: str | None = None,
        only_undownloaded: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> RecordPage:
        conn = self._open_app_db()
        try:
            return SearchService(conn).list_records(
                record_id=record_id,
                title=title,
                actor=actor,
                source=source,
                date_from=date_from,
                date_to=date_to,
                downloaded=downloaded,
                file_type=file_type,
                only_undownloaded=only_undownloaded,
                page=page,
                page_size=page_size,
            )
        finally:
            conn.close()

    def search_title(self, keyword: str, limit: int = 50) -> list[RecordSummary]:
        conn = self._open_app_db()
        try:
            return SearchService(conn).search_title(keyword, limit)
        finally:
            conn.close()

    def search_source(self, source: str, limit: int = 50) -> list[RecordSummary]:
        conn = self._open_app_db()
        try:
            return SearchService(conn).search_source(source, limit)
        finally:
            conn.close()

    def search_date(
        self,
        date_from: str | None,
        date_to: str | None,
        limit: int = 50,
    ) -> list[RecordSummary]:
        conn = self._open_app_db()
        try:
            return SearchService(conn).search_date(date_from, date_to, limit)
        finally:
            conn.close()

    def list_undownloaded(
        self,
        actor: str | None = None,
        source: str | None = None,
        limit: int = 50,
        actor_id: int | None = None,
    ) -> list[RecordSummary]:
        conn = self._open_app_db()
        try:
            return SearchService(conn).list_undownloaded(actor=actor, actor_id=actor_id, source=source, limit=limit)
        finally:
            conn.close()

    def info(self, record_id_or_key: str) -> RecordDetail:
        conn = self._open_app_db()
        try:
            return SearchService(conn).get_info(record_id_or_key)
        finally:
            conn.close()

    def build_download_plan(
        self,
        record_id_or_key: str,
        include_par2: bool = False,
        types: str | None = None,
        output: Path | None = None,
        only_undownloaded: bool = False,
    ) -> DownloadPlan:
        app_config = config_module.load_config(Path("env/config.toml"))
        conn = self._open_app_db()
        try:
            return SearchService(conn).build_download_plan(
                record_id_or_key=record_id_or_key,
                downloads_dir=app_config.downloads_dir,
                include_par2_by_default=app_config.include_par2_by_default,
                include_par2=include_par2,
                type_filter_text=types,
                output_dir=output,
                safety_margin_percent=app_config.safety_margin_percent,
                safety_margin_min_mb=app_config.safety_margin_min_mb,
                only_undownloaded=only_undownloaded,
            )
        finally:
            conn.close()

    def download(
        self,
        record_id_or_key: str,
        include_par2: bool = False,
        types: str | None = None,
        output: Path | None = None,
        assume_yes: bool = False,
        confirm_callback=None,
        only_undownloaded: bool = False,
        output_callback: Callable[[str], None] | None = None,
    ) -> DownloadExecutionResult:
        app_config = config_module.load_config(Path("env/config.toml"))
        plan = self.build_download_plan(record_id_or_key, include_par2, types, output, only_undownloaded)
        conn = self._open_app_db()
        downloads = DownloadRepository(conn)
        try:
            try:
                mega_whoami = mega.resolve_executable(app_config.mega_whoami)
                mega_get = mega.resolve_executable(app_config.mega_get)
            except ExternalToolError as error:
                download_id = downloads.create_from_plan(plan, "blocked", str(error))
                conn.commit()
                return DownloadExecutionResult(
                    download_id=download_id,
                    record_group_id=plan.record_group_id,
                    status="blocked",
                    completed=0,
                    failed=0,
                    output_dir=plan.output_dir,
                    message=str(error),
                )

            login = mega.check_login(mega_whoami)
            if not login.logged_in:
                message = "MEGA is not logged in. Use Settings or run mega-login."
                download_id = downloads.create_from_plan(plan, "blocked", message)
                conn.commit()
                return DownloadExecutionResult(
                    download_id=download_id,
                    record_group_id=plan.record_group_id,
                    status="blocked",
                    completed=0,
                    failed=0,
                    output_dir=plan.output_dir,
                    message=message,
                )

            if plan.free_bytes_before is not None and plan.free_bytes_before < plan.required_bytes:
                message = (
                    f"Insufficient disk space: required={plan.required_bytes} "
                    f"free={plan.free_bytes_before}"
                )
                download_id = downloads.create_from_plan(plan, "blocked", message)
                conn.commit()
                return DownloadExecutionResult(
                    download_id=download_id,
                    record_group_id=plan.record_group_id,
                    status="blocked",
                    completed=0,
                    failed=0,
                    output_dir=plan.output_dir,
                    message=message,
                )

            if not assume_yes and confirm_callback is not None and not confirm_callback(plan):
                download_id = downloads.create_from_plan(plan, "cancelled", "Cancelled by user.")
                conn.commit()
                return DownloadExecutionResult(
                    download_id=download_id,
                    record_group_id=plan.record_group_id,
                    status="cancelled",
                    completed=0,
                    failed=0,
                    output_dir=plan.output_dir,
                    message="Cancelled by user.",
                )

            plan.output_dir.mkdir(parents=True, exist_ok=True)
            download_id = downloads.create_from_plan(plan, "planned")
            completed = 0
            failed = 0
            last_exit_code: int | None = None
            for link in plan.selected_links:
                item_id = downloads.create_download_item(download_id, link.id)
                downloads.start_download_item(item_id)
                try:
                    result = mega.download_link(
                        mega_get,
                        link.mega_url,
                        plan.output_dir,
                        output_callback=output_callback,
                    )
                except Exception as error:
                    result = MegaCommandResult(1, "", str(error))
                last_exit_code = result.exit_code
                message = _command_message(result.stdout, result.stderr)
                if result.exit_code == 0:
                    completed += 1
                    downloads.finish_download_item(item_id, "completed", result.exit_code, message)
                else:
                    failed += 1
                    downloads.finish_download_item(item_id, "failed", result.exit_code, message)

            status = "completed" if failed == 0 else "failed"
            downloads.update_download_status(
                download_id,
                status,
                last_exit_code,
                f"completed={completed} failed={failed}",
            )
            conn.commit()
            return DownloadExecutionResult(
                download_id=download_id,
                record_group_id=plan.record_group_id,
                status=status,
                completed=completed,
                failed=failed,
                output_dir=plan.output_dir,
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def list_downloads(
        self,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        record_id: int | None = None,
    ) -> DownloadPage:
        normalized_page = normalize_page(page)
        normalized_page_size = normalize_limit(page_size)
        if record_id is not None and record_id < 1:
            raise ValidationError("Record id must be at least 1.")
        conn = self._open_app_db()
        try:
            repo = DownloadRepository(conn)
            total = repo.count_downloads(status=status, record_id=record_id)
            offset = (normalized_page - 1) * normalized_page_size
            items = repo.list_downloads(
                normalized_page_size,
                offset,
                status=status,
                record_id=record_id,
            )
            total_pages = (total + normalized_page_size - 1) // normalized_page_size if total else 0
            return DownloadPage(items=items, page=normalized_page, page_size=normalized_page_size, total=total, total_pages=total_pages)
        finally:
            conn.close()

    def get_download(self, download_id: int):
        if download_id < 1:
            raise ValidationError("Download id must be at least 1.")
        conn = self._open_app_db()
        try:
            result = DownloadRepository(conn).get_download(download_id)
            if result is None:
                raise NotFoundError(f"Download not found: {download_id}")
            return result
        finally:
            conn.close()

    def list_download_items(self, download_id: int) -> list[DownloadItemDetail]:
        if download_id < 1:
            raise ValidationError("Download id must be at least 1.")
        conn = self._open_app_db()
        try:
            repo = DownloadRepository(conn)
            if repo.get_download(download_id) is None:
                raise NotFoundError(f"Download not found: {download_id}")
            return repo.list_download_items(download_id)
        finally:
            conn.close()

    def download_actor(
        self,
        actor_id: int,
        limit: int = 3,
        include_par2: bool = False,
        types: str | None = None,
        output: Path | None = None,
        assume_yes: bool = False,
        confirm_callback=None,
        output_callback: Callable[[str], None] | None = None,
    ) -> ActorDownloadResult:
        records = self.list_undownloaded(actor_id=actor_id, limit=limit)
        if not records:
            return ActorDownloadResult(
                actor_id=actor_id,
                selected_count=0,
                results=[],
                message=f"No undownloaded records found for actor id {actor_id}.",
            )

        results: list[DownloadExecutionResult] = []
        for record in records:
            record_output = (output / str(record.id)) if output is not None else None
            results.append(
                self.download(
                    str(record.id),
                    include_par2=include_par2,
                    types=types,
                    output=record_output,
                    assume_yes=assume_yes,
                    confirm_callback=confirm_callback,
                    only_undownloaded=True,
                    output_callback=output_callback,
                )
            )
        return ActorDownloadResult(
            actor_id=actor_id,
            selected_count=len(records),
            results=results,
        )

    def _create_importer(self, path: Path):
        extension = path.suffix.casefold()
        if extension in {".xlsx", ".xlsm"}:
            return "xlsx", ExcelImporter()
        if extension in {".db", ".sqlite", ".sqlite3"}:
            return "legacy_db", LegacyDbImporter()
        if extension == ".json":
            return "json", JsonImporter()
        raise ValidationError(f"Unsupported import file extension: {extension}")

    def _open_app_db(self):
        app_config = config_module.load_config(Path("env/config.toml"))
        if not app_config.database_path.exists():
            raise ConfigError(f"Database file does not exist: {app_config.database_path}")
        conn = db.connect(app_config.database_path)
        return conn


def _import_excel_records(
    importer: ExcelImporter,
    source_path: Path,
    service: ImportService,
    import_id: int,
    stats: ImportStats,
    progress_callback: Callable[[ImportProgress], None] | None,
    total_rows: int | None,
    source_type: str,
) -> None:
    records_by_key = {}
    duplicate_keys: set[str] = set()
    duplicate_rows = 0
    read_total = total_rows or 0
    for record in importer.iter_records(source_path):
        stats.total_rows += 1
        if isinstance(record, ImportRowError):
            service.record_error(import_id, record)
            stats.error_count += 1
        else:
            source_key = build_source_key(record)
            if source_key in records_by_key:
                duplicate_keys.add(source_key)
                duplicate_rows += 1
                records_by_key[source_key] = _merge_import_records(records_by_key[source_key], record)
            else:
                records_by_key[source_key] = record
        _report_import_progress(
            progress_callback,
            source_type,
            source_path,
            stats.total_rows,
            total_rows,
            "Reading",
        )

    importer.duplicate_source_keys = len(duplicate_keys)
    importer.duplicate_rows_merged = duplicate_rows
    write_total = len(records_by_key)
    combined_total = read_total + write_total if total_rows is not None else None
    _report_import_progress(
        progress_callback,
        source_type,
        source_path,
        stats.total_rows,
        combined_total,
        "Writing",
    )
    written = 0
    for record in records_by_key.values():
        try:
            result = service.upsert_record(import_id, record)
        except ImportRowError as error:
            service.record_error(import_id, error)
            stats.error_count += 1
        else:
            apply_upsert_result(stats, result)
        written += 1
        _report_import_progress(
            progress_callback,
            source_type,
            source_path,
            stats.total_rows + written,
            combined_total,
            "Writing",
        )


def _merge_import_records(first, second):
    links_by_key = {}
    for link in first.links + second.links:
        key = clean_text(link.mega_url)
        if key is None or key in links_by_key:
            continue
        links_by_key[key] = link
    merged_links = [
        LinkItem(
            link_order=index,
            mega_url=link.mega_url,
            file_type=normalize_file_type(link.file_type),
            size_bytes=link.size_bytes,
            formatted_size=clean_text(link.formatted_size),
        )
        for index, link in enumerate(links_by_key.values(), start=1)
    ]
    return replace(first, links=merged_links)


def _import_notes(importer) -> str | None:
    notes: list[str] = []
    extra_note = _extra_columns_note(getattr(importer, "extra_columns", ()))
    if extra_note is not None:
        notes.append(extra_note)
    duplicate_source_keys = getattr(importer, "duplicate_source_keys", 0)
    duplicate_rows_merged = getattr(importer, "duplicate_rows_merged", 0)
    if duplicate_rows_merged:
        notes.append(
            f"Duplicate Excel records merged: {duplicate_source_keys} source keys, "
            f"{duplicate_rows_merged} extra rows"
        )
    return "; ".join(notes) if notes else None


def _extra_columns_note(extra_columns: tuple[str, ...]) -> str | None:
    if not extra_columns:
        return None
    return "Extra Excel columns ignored: " + ", ".join(extra_columns)


def _count_import_rows(importer, source_path: Path) -> int | None:
    if hasattr(importer, "count_records"):
        return importer.count_records(source_path)
    if hasattr(importer, "count_rows"):
        return importer.count_rows(source_path)
    return None


def _report_import_progress(
    progress_callback: Callable[[ImportProgress], None] | None,
    source_type: str,
    source_path: Path,
    completed_rows: int,
    total_rows: int | None,
    phase: str,
) -> None:
    if progress_callback is None:
        return
    progress_callback(
        ImportProgress(
            source_type=source_type,
            source_path=source_path,
            completed_rows=completed_rows,
            total_rows=total_rows,
            phase=phase,
        )
    )


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


def _check_writable_dir(name: str, path: Path) -> DoctorCheck:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".recordtree_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as error:
        return DoctorCheck(name, "fail", str(error))
    return DoctorCheck(name, "pass", str(path))


def _check_executable(name: str, configured: str) -> tuple[DoctorCheck, str | None]:
    try:
        resolved = mega.resolve_executable(configured)
    except ExternalToolError as error:
        return DoctorCheck(name, "fail", str(error)), None
    return DoctorCheck(name, "pass", resolved), resolved


def _mega_command_status(configured: str) -> MegaCommandStatus:
    try:
        resolved = mega.resolve_executable(configured)
    except ExternalToolError as error:
        return MegaCommandStatus(
            configured=configured,
            resolved=None,
            available=False,
            message=str(error),
        )
    return MegaCommandStatus(
        configured=configured,
        resolved=resolved,
        available=True,
        message=resolved,
    )


def _megacmd_persistence_dir() -> Path:
    home = Path.home()
    if os.name != "nt" and home == Path("/root"):
        return home
    return home / ".megaCmd"


def _command_message(stdout: str, stderr: str) -> str | None:
    message = "\n".join(part for part in (stdout, stderr) if part)
    return message or None
