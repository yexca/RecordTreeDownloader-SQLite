from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .app import RecordTreeApp
from .exceptions import ConfigError, NotFoundError, NotImplementedFeatureError, RecordTreeError

app = typer.Typer(
    help="Local SQLite-backed Record Tree downloader.",
    no_args_is_help=True,
)
console = Console()


def _handle_error(error: RecordTreeError) -> None:
    console.print(f"[red]Error:[/red] {error}")
    if isinstance(error, ConfigError):
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
        RecordTreeApp().doctor()
    except NotImplementedFeatureError as error:
        console.print(f"[yellow]{error}[/yellow]")
    except RecordTreeError as error:
        _handle_error(error)


@app.command(name="import")
def import_command(path: Path) -> None:
    """Import a Record Tree workbook, JSON export, or legacy SQLite DB."""
    try:
        result = RecordTreeApp().import_file(path)
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
        console.print(table)


@app.command()
def stats() -> None:
    """Show database statistics."""
    try:
        RecordTreeApp().stats()
    except NotImplementedFeatureError as error:
        console.print(f"[yellow]{error}[/yellow]")
    except RecordTreeError as error:
        _handle_error(error)
