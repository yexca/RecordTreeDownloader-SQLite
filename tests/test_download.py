from __future__ import annotations

from pathlib import Path

import pytest

from recordtree.app import RecordTreeApp
from recordtree.db import connect
from recordtree.exceptions import ValidationError
from recordtree.importer.service import ImportService
from recordtree.models import ImportRecord, LinkItem, MegaCommandResult, MegaLoginStatus
from recordtree.repositories import ImportRepository


def _record() -> ImportRecord:
    return ImportRecord(
        source_type="xlsx",
        actor_raw="Download Actor",
        delivery_date="2026-01-02",
        title="Download title",
        entry_date="2026-01-03",
        note=None,
        upload_title="Download upload",
        duplicate_search_raw=None,
        source_name="Source",
        size_raw=None,
        size_bytes=600,
        mega_file_name="bundle",
        mega_total_bytes=600,
        mega_formatted_size=None,
        mega_json="{}",
        source_row_number=2,
        links=[
            LinkItem(1, "https://example.invalid/d/1", ".mp4", 100, "100 B"),
            LinkItem(2, "https://example.invalid/d/2", ".m4a", 200, "200 B"),
            LinkItem(3, "https://example.invalid/d/3", ".par2", 300, "300 B"),
        ],
    )


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.chdir(tmp_path)
    RecordTreeApp().init()
    conn = connect(tmp_path / "env" / "recordtree.sqlite3")
    try:
        source = tmp_path / "fixture.xlsx"
        source.write_bytes(b"xlsx placeholder")
        import_id = ImportRepository(conn).create_import("xlsx", source)
        ImportService(conn).upsert_record(import_id, _record())
        group_id = int(conn.execute("SELECT id FROM record_groups").fetchone()[0])
        conn.commit()
        return group_id
    finally:
        conn.close()


def test_download_plan_filters_and_required_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    group_id = _setup(tmp_path, monkeypatch)
    app = RecordTreeApp()

    default_plan = app.build_download_plan(str(group_id))
    assert [link.file_type for link in default_plan.selected_links] == [".mp4", ".m4a"]
    assert default_plan.selected_bytes == 300
    assert default_plan.margin_bytes == 512 * 1024 * 1024

    par2_plan = app.build_download_plan(str(group_id), include_par2=True)
    assert [link.file_type for link in par2_plan.selected_links] == [".mp4", ".m4a", ".par2"]

    typed = app.build_download_plan(str(group_id), types="mp4,m4a")
    assert {link.file_type for link in typed.selected_links} == {".mp4", ".m4a"}

    with pytest.raises(ValidationError) as error:
        app.build_download_plan(str(group_id), types="par2")
    assert "No links selected" in str(error.value)


def test_download_success_failure_and_preflight_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group_id = _setup(tmp_path, monkeypatch)
    calls: list[str] = []
    monkeypatch.setattr("recordtree.mega.resolve_executable", lambda configured: configured)
    monkeypatch.setattr(
        "recordtree.mega.check_login",
        lambda _whoami: MegaLoginStatus(True, 0, "Account: test"),
    )

    def fake_download(_mega_get: str, url: str, _output_dir: Path) -> MegaCommandResult:
        calls.append(url)
        if url.endswith("/2"):
            return MegaCommandResult(1, "bad", "failed")
        return MegaCommandResult(0, "ok", "")

    monkeypatch.setattr("recordtree.mega.download_link", fake_download)

    result = RecordTreeApp().download(str(group_id), types="mp4,m4a", assume_yes=True)

    assert result.status == "failed"
    assert result.completed == 1
    assert result.failed == 1
    assert len(calls) == 2

    conn = connect(tmp_path / "env" / "recordtree.sqlite3")
    try:
        assert conn.execute("SELECT status FROM downloads WHERE id = ?", (result.download_id,)).fetchone()[0] == "failed"
        statuses = {
            row["status"]
            for row in conn.execute("SELECT status FROM download_items").fetchall()
        }
        assert {"completed", "failed"} <= statuses
    finally:
        conn.close()

    calls.clear()
    monkeypatch.setattr(
        "recordtree.mega.check_login",
        lambda _whoami: MegaLoginStatus(False, 1, "not logged in"),
    )
    blocked = RecordTreeApp().download(str(group_id), types="mp4", assume_yes=True)
    assert blocked.status == "blocked"
    assert calls == []


def test_download_cancelled_records_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    group_id = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr("recordtree.mega.resolve_executable", lambda configured: configured)
    monkeypatch.setattr(
        "recordtree.mega.check_login",
        lambda _whoami: MegaLoginStatus(True, 0, "Account: test"),
    )
    monkeypatch.setattr(
        "recordtree.mega.download_link",
        lambda *_args: MegaCommandResult(0, "ok", ""),
    )

    result = RecordTreeApp().download(
        str(group_id),
        types="mp4",
        assume_yes=False,
        confirm_callback=lambda _plan: False,
    )

    assert result.status == "cancelled"
    assert not (tmp_path / "downloads" / str(group_id)).exists()
    conn = connect(tmp_path / "env" / "recordtree.sqlite3")
    try:
        assert conn.execute("SELECT status FROM downloads WHERE id = ?", (result.download_id,)).fetchone()[0] == "cancelled"
    finally:
        conn.close()
