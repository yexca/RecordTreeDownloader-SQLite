from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, ProgressColumn, Task, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.text import Text
from rich.table import Table

from .app import RecordTreeApp
from .exceptions import ConfigError, NotFoundError, NotImplementedFeatureError, RecordTreeError, ValidationError
from .models import (
    ActorDownloadResult,
    DoctorResult,
    DownloadExecutionResult,
    DownloadPlan,
    ImportProgress,
    RecordDetail,
    RecordSummary,
    StatsResult,
)
from .search import preview_url
from .sizes import format_bytes

app = typer.Typer(
    help="Local SQLite-backed Record Tree downloader.",
    no_args_is_help=True,
)
console = Console()


class RowCountColumn(ProgressColumn):
    def render(self, task: Task) -> Text:
        completed = int(task.completed)
        if task.total is None:
            return Text(f"{completed} steps")
        return Text(f"{completed}/{int(task.total)} steps")


def _handle_error(error: RecordTreeError) -> None:
    console.print(f"[red]Error:[/red] {error}")
    if isinstance(error, (ConfigError, ValidationError)):
        raise typer.Exit(2)
    if isinstance(error, NotFoundError):
        raise typer.Exit(3)
    raise typer.Exit(10)


@app.command()
def init() -> None:
    """Create local config, database, download, and log paths."""
    try:
        result = RecordTreeApp().init()
    except NotImplementedFeatureError as error:
        console.print(f"[yellow]{error}[/yellow]")
    except RecordTreeError as error:
        _handle_error(error)
    else:
        table = Table(title="RecordTree initialized")
        table.add_column("Item", style="cyan")
        table.add_column("Path")
        table.add_row("Config", str(result.config_path))
        table.add_row("Database", str(result.database_path))
        table.add_row("Downloads", str(result.downloads_dir))
        table.add_row("Logs", str(result.logs_dir))
        table.add_row("Schema", result.schema_version)
        console.print(table)


@app.command()
def doctor() -> None:
    """Check local configuration and external dependencies."""
    try:
        result = RecordTreeApp().doctor()
    except NotImplementedFeatureError as error:
        console.print(f"[yellow]{error}[/yellow]")
    except RecordTreeError as error:
        _handle_error(error)
    else:
        _print_doctor(result)
        if not result.ok:
            raise typer.Exit(4)


@app.command(name="import")
def import_command(path: Path) -> None:
    """Import a Record Tree workbook, JSON export, or legacy SQLite DB."""
    try:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            RowCountColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Importing", total=None)

            def update_progress(event: ImportProgress) -> None:
                progress.update(
                    task_id,
                    completed=event.completed_rows,
                    total=event.total_rows,
                    description=f"{event.phase} {event.source_type}",
                )

            result = RecordTreeApp().import_file(path, progress_callback=update_progress)
    except NotImplementedFeatureError as error:
        console.print(f"[yellow]{error}[/yellow]")
    except RecordTreeError as error:
        _handle_error(error)
    else:
        table = Table(title="Import summary")
        table.add_column("Item", style="cyan")
        table.add_column("Value")
        table.add_row("Import ID", str(result.import_id))
        table.add_row("Source", str(result.source_path))
        table.add_row("Status", result.status)
        table.add_row("Total rows", str(result.stats.total_rows))
        table.add_row("Inserted groups", str(result.stats.inserted_groups))
        table.add_row("Updated groups", str(result.stats.updated_groups))
        table.add_row("Link sets changed", str(result.stats.link_sets_changed))
        table.add_row("Inserted links", str(result.stats.inserted_links))
        table.add_row("Skipped links", str(result.stats.skipped_links))
        table.add_row("Errors", str(result.stats.error_count))
        if result.error_csv_path is not None:
            table.add_row("Error CSV", str(result.error_csv_path))
        if result.extra_columns:
            table.add_row("Extra columns", ", ".join(result.extra_columns))
        if result.notes:
            table.add_row("Notes", result.notes)
        console.print(table)


@app.command()
def stats() -> None:
    """Show database statistics."""
    try:
        result = RecordTreeApp().stats()
    except NotImplementedFeatureError as error:
        console.print(f"[yellow]{error}[/yellow]")
    except RecordTreeError as error:
        _handle_error(error)
    else:
        _print_stats(result)


@app.command(name="search-actor")
def search_actor(name: str, limit: int = 50) -> None:
    """Search records by actor name."""
    try:
        rows = RecordTreeApp().search_actor(name, limit)
    except RecordTreeError as error:
        _handle_error(error)
    else:
        _print_record_rows("Actor search", rows)


@app.command(name="search-title")
def search_title(keyword: str, limit: int = 50) -> None:
    """Search records by title or upload title."""
    try:
        rows = RecordTreeApp().search_title(keyword, limit)
    except RecordTreeError as error:
        _handle_error(error)
    else:
        _print_record_rows("Title search", rows)


@app.command(name="search-source")
def search_source(source: str, limit: int = 50) -> None:
    """Search records by source name."""
    try:
        rows = RecordTreeApp().search_source(source, limit)
    except RecordTreeError as error:
        _handle_error(error)
    else:
        _print_record_rows("Source search", rows)


@app.command(name="search-date")
def search_date(
    date_from: str | None = typer.Option(None, "--from"),
    date_to: str | None = typer.Option(None, "--to"),
    limit: int = 50,
) -> None:
    """Search records by delivery date range."""
    try:
        rows = RecordTreeApp().search_date(date_from, date_to, limit)
    except RecordTreeError as error:
        _handle_error(error)
    else:
        _print_record_rows("Date search", rows)


@app.command(name="list-undownload")
@app.command(name="list-undownloaded")
def list_undownloaded(
    actor: str | None = None,
    actor_id: int | None = typer.Option(None, "--actor-id"),
    source: str | None = None,
    limit: int = 50,
) -> None:
    """List records with active links not marked completed."""
    try:
        rows = RecordTreeApp().list_undownloaded(actor=actor, actor_id=actor_id, source=source, limit=limit)
    except RecordTreeError as error:
        _handle_error(error)
    else:
        _print_record_rows("Undownloaded records", rows)


@app.command()
def info(record_id_or_key: str) -> None:
    """Show record details and active links."""
    try:
        detail = RecordTreeApp().info(record_id_or_key)
    except RecordTreeError as error:
        _handle_error(error)
    else:
        _print_record_detail(detail)


@app.command()
def download(
    record_id_or_key: str | None = typer.Argument(None),
    actor: int | None = typer.Option(None, "--actor", "-actor"),
    count: int = typer.Option(3, "--count", "--limit"),
    include_par2: bool = typer.Option(False, "--include-par2"),
    types: str | None = typer.Option(None, "--types"),
    output: Path | None = typer.Option(None, "--output"),
    yes: bool = typer.Option(False, "--yes"),
) -> None:
    """Download selected active links through MEGAcmd."""
    app_service = RecordTreeApp()

    def confirm(plan: DownloadPlan) -> bool:
        _print_download_plan(plan)
        return typer.confirm("Continue with download?")

    try:
        if record_id_or_key is None and actor is None:
            raise ValidationError("download requires a record id or --actor.")
        if record_id_or_key is not None and actor is not None:
            raise ValidationError("Use either a record id or --actor, not both.")
        if actor is not None:
            result = app_service.download_actor(
                actor,
                limit=count,
                include_par2=include_par2,
                types=types,
                output=output,
                assume_yes=yes,
                confirm_callback=None if yes else confirm,
                output_callback=_print_process_output,
            )
        else:
            result = app_service.download(
                record_id_or_key,
                include_par2=include_par2,
                types=types,
                output=output,
                assume_yes=yes,
                confirm_callback=None if yes else confirm,
                output_callback=_print_process_output,
            )
    except RecordTreeError as error:
        _handle_error(error)
    else:
        if isinstance(result, ActorDownloadResult):
            _print_actor_download_result(result)
            statuses = {item.status for item in result.results}
            if "blocked" in statuses:
                raise typer.Exit(5)
            if "failed" in statuses:
                raise typer.Exit(10)
            return
        _print_download_result(result)
        if result.status == "blocked":
            raise typer.Exit(5)
        if result.status == "failed":
            raise typer.Exit(10)


def _dash(value: object | None) -> str:
    if value is None:
        return "-"
    text = str(value)
    return text if text else "-"


def _print_process_output(text: str) -> None:
    console.file.write(text)
    console.file.flush()


def _print_record_rows(title: str, rows: list[RecordSummary]) -> None:
    table = Table(title=title)
    table.add_column("id", style="cyan")
    table.add_column("delivery_date")
    table.add_column("actor")
    table.add_column("title")
    table.add_column("source")
    table.add_column("size")
    table.add_column("active_links")
    table.add_column("downloaded")
    for row in rows:
        table.add_row(
            str(row.id),
            _dash(row.delivery_date),
            _dash(row.actor),
            row.title,
            _dash(row.source),
            format_bytes(row.size_bytes),
            str(row.active_links),
            row.downloaded,
        )
    console.print(table)


def _print_doctor(result: DoctorResult) -> None:
    table = Table(title="Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Message")
    for check in result.checks:
        table.add_row(check.name, check.status, check.message)
    console.print(table)


def _print_record_detail(detail: RecordDetail) -> None:
    table = Table(title="Record group")
    table.add_column("Item", style="cyan")
    table.add_column("Value")
    table.add_row("id", str(detail.id))
    table.add_row("source_key", detail.source_key)
    table.add_row("actor", detail.actor)
    table.add_row("delivery_date", _dash(detail.delivery_date))
    table.add_row("entry_date", _dash(detail.entry_date))
    table.add_row("title", detail.title)
    table.add_row("source", detail.source)
    table.add_row("upload_title", detail.upload_title)
    table.add_row("note", _dash(detail.note))
    table.add_row("size", format_bytes(detail.size_bytes))
    table.add_row("active_links", str(detail.active_links))
    table.add_row("downloaded", detail.downloaded)
    console.print(table)

    link_table = Table(title="Active links")
    link_table.add_column("order", style="cyan")
    link_table.add_column("type")
    link_table.add_column("size")
    link_table.add_column("status")
    link_table.add_column("url")
    for link in detail.links:
        link_table.add_row(
            str(link.link_order),
            _dash(link.file_type),
            format_bytes(link.size_bytes),
            link.status,
            preview_url(link.mega_url),
        )
    console.print(link_table)
    if detail.inactive_link_count:
        console.print(f"Historical inactive links: {detail.inactive_link_count}")


def _print_stats(result: StatsResult) -> None:
    table = Table(title="RecordTree stats")
    table.add_column("Item", style="cyan")
    table.add_column("Value")
    table.add_row("Record groups", str(result.total_record_groups))
    table.add_row("Active links", str(result.active_link_count))
    table.add_row("Inactive historical links", str(result.inactive_link_count))
    table.add_row("Actors", str(result.actor_count))
    table.add_row("Sources", str(result.source_count))
    table.add_row("Downloaded all", str(result.downloaded_all))
    table.add_row("Downloaded partial", str(result.downloaded_partial))
    table.add_row("Downloaded none", str(result.downloaded_none))
    table.add_row("Downloaded unknown", str(result.downloaded_unknown))
    console.print(table)

    imports = Table(title="Recent imports")
    imports.add_column("id", style="cyan")
    imports.add_column("type")
    imports.add_column("file")
    imports.add_column("started_at")
    imports.add_column("status")
    imports.add_column("rows")
    imports.add_column("errors")
    for item in result.recent_imports:
        imports.add_row(
            str(item.id),
            item.source_type,
            item.source_file_name,
            item.started_at,
            item.status,
            str(item.total_rows),
            str(item.error_count),
        )
    console.print(imports)

    downloads = Table(title="Recent downloads")
    downloads.add_column("id", style="cyan")
    downloads.add_column("record")
    downloads.add_column("requested_at")
    downloads.add_column("status")
    downloads.add_column("selected")
    downloads.add_column("message")
    for item in result.recent_downloads:
        downloads.add_row(
            str(item.id),
            str(item.record_group_id),
            item.requested_at,
            item.status,
            format_bytes(item.selected_bytes),
            _dash(item.message),
        )
    console.print(downloads)


def _print_download_plan(plan: DownloadPlan) -> None:
    table = Table(title="Download plan")
    table.add_column("Item", style="cyan")
    table.add_column("Value")
    table.add_row("Record", f"{plan.record_group_id} {plan.actor} {plan.title}")
    table.add_row("Output", str(plan.output_dir))
    table.add_row("Files", str(len(plan.selected_links)))
    types = sorted({link.file_type or "-" for link in plan.selected_links})
    table.add_row("Types", ", ".join(types))
    table.add_row("Selected size", format_bytes(plan.selected_bytes))
    table.add_row("Safety margin", format_bytes(plan.margin_bytes))
    table.add_row("Required", format_bytes(plan.required_bytes))
    table.add_row("Free", format_bytes(plan.free_bytes_before))
    table.add_row("Exclude .par2", "no" if plan.include_par2 else "yes")
    console.print(table)


def _print_download_result(result: DownloadExecutionResult) -> None:
    table = Table(title="Download summary")
    table.add_column("Item", style="cyan")
    table.add_column("Value")
    table.add_row("Download ID", str(result.download_id))
    table.add_row("Record group", str(result.record_group_id))
    table.add_row("Status", result.status)
    table.add_row("Completed", str(result.completed))
    table.add_row("Failed", str(result.failed))
    table.add_row("Output", str(result.output_dir))
    if result.message:
        table.add_row("Message", result.message)
    console.print(table)


def _print_actor_download_result(result: ActorDownloadResult) -> None:
    if result.message:
        console.print(f"[yellow]{result.message}[/yellow]")
        return

    table = Table(title="Actor download summary")
    table.add_column("Record group", style="cyan")
    table.add_column("Download ID")
    table.add_column("Status")
    table.add_column("Completed")
    table.add_column("Failed")
    table.add_column("Output")
    for item in result.results:
        table.add_row(
            str(item.record_group_id),
            str(item.download_id),
            item.status,
            str(item.completed),
            str(item.failed),
            str(item.output_dir),
        )
    console.print(table)
