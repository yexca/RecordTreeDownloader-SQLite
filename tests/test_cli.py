from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from recordtree.cli import app
from recordtree.app import RecordTreeApp
from recordtree.db import connect
from recordtree.importer.service import ImportService
from recordtree.models import ActorDownloadResult, ImportRecord, LinkItem
from recordtree.repositories import ImportRepository


def _record(actor: str = "CLI Actor") -> ImportRecord:
    return ImportRecord(
        source_type="xlsx",
        actor_raw=actor,
        delivery_date="2026-01-02",
        title="CLI title",
        entry_date="2026-01-03",
        note=None,
        upload_title="CLI upload",
        duplicate_search_raw=None,
        source_name="Source",
        size_raw=None,
        size_bytes=100,
        mega_file_name="cli",
        mega_total_bytes=100,
        mega_formatted_size=None,
        mega_json="{}",
        source_row_number=2,
        links=[LinkItem(1, "https://example.invalid/cli/1", ".mp4", 100, "100 B")],
    )


def _setup_record(tmp_path: Path, monkeypatch) -> int:
    monkeypatch.chdir(tmp_path)
    RecordTreeApp().init()
    conn = connect(tmp_path / "env" / "recordtree.sqlite3")
    try:
        source = tmp_path / "fixture.xlsx"
        source.write_bytes(b"xlsx placeholder")
        import_id = ImportRepository(conn).create_import("xlsx", source)
        ImportService(conn).upsert_record(import_id, _record())
        actor_id = int(conn.execute("SELECT id FROM actors WHERE name = ?", ("CLI Actor",)).fetchone()[0])
        conn.commit()
        return actor_id
    finally:
        conn.close()


def test_cli_init_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    first = runner.invoke(app, ["init"])
    second = runner.invoke(app, ["init"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "RecordTree initialized" in first.output
    assert (tmp_path / "env" / "recordtree.sqlite3").exists()


def test_cli_unsupported_import_extension_returns_exit_code_2(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "fixture.txt"
    source.write_text("not importable", encoding="utf-8")

    result = CliRunner().invoke(app, ["import", str(source)])

    assert result.exit_code == 2
    assert "Unsupported import file extension" in result.output


def test_cli_missing_info_target_returns_exit_code_3(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["info", "999999"])

    assert result.exit_code == 3
    assert "Record not found" in result.output


def test_cli_search_limit_below_one_returns_exit_code_2(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["search-actor", "actor", "--limit", "0"])

    assert result.exit_code == 2
    assert "Limit must be at least 1" in result.output


def test_cli_search_actor_lists_actor_ids(tmp_path: Path, monkeypatch) -> None:
    actor_id = _setup_record(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["search-actor", "cli"])

    assert result.exit_code == 0
    assert "Actor search" in result.output
    assert str(actor_id) in result.output
    assert "CLI Actor" in result.output
    assert "CLI title" not in result.output


def test_cli_actor_records_lists_records_by_actor_id(tmp_path: Path, monkeypatch) -> None:
    actor_id = _setup_record(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["actor-records", str(actor_id)])

    assert result.exit_code == 0
    assert "Actor records" in result.output


def test_cli_download_requires_record_or_actor(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["download"])

    assert result.exit_code == 2
    assert "download requires a record id or --actor" in result.output


def test_cli_list_undownload_alias_accepts_actor_id(tmp_path: Path, monkeypatch) -> None:
    actor_id = _setup_record(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["list-undownload", "--actor-id", str(actor_id)])

    assert result.exit_code == 0
    assert "Undownloaded records" in result.output


def test_cli_download_accepts_single_dash_actor(monkeypatch) -> None:
    monkeypatch.setattr(
        RecordTreeApp,
        "download_actor",
        lambda self, actor_id, **_kwargs: ActorDownloadResult(
            actor_id=actor_id,
            selected_count=0,
            results=[],
            message=f"No undownloaded records found for actor id {actor_id}.",
        ),
    )

    result = CliRunner().invoke(app, ["download", "-actor", "7", "--yes"])

    assert result.exit_code == 0
    assert "No undownloaded records found for actor id 7" in result.output


def test_cli_download_record_and_actor_are_mutually_exclusive(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["download", "123", "--actor", "7"])

    assert result.exit_code == 2
    assert "Use either a record id or --actor, not both" in result.output
