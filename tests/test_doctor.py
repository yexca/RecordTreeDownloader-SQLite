from __future__ import annotations

from pathlib import Path

from recordtree.app import RecordTreeApp
from recordtree.models import MegaLoginStatus


def test_doctor_reports_passes_with_mocked_mega(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    RecordTreeApp().init()
    monkeypatch.setattr("recordtree.mega.resolve_executable", lambda configured: configured)
    monkeypatch.setattr(
        "recordtree.mega.check_login",
        lambda _whoami: MegaLoginStatus(True, 0, "Account: test"),
    )

    result = RecordTreeApp().doctor()

    assert result.ok is True
    statuses = {check.name: check.status for check in result.checks}
    assert statuses["config"] == "pass"
    assert statuses["database"] == "pass"
    assert statuses["schema"] == "pass"
    assert statuses["mega_login"] == "pass"
