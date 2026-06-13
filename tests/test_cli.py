from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from recordtree.cli import app


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
