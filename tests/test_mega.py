from __future__ import annotations

from pathlib import Path

from recordtree import mega


class Completed:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_check_login_and_download_use_subprocess_lists(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(args, shell, capture_output, text, timeout):
        calls.append(
            {
                "args": args,
                "shell": shell,
                "capture_output": capture_output,
                "text": text,
                "timeout": timeout,
            }
        )
        return Completed(0, "logged in", "")

    monkeypatch.setattr("subprocess.run", fake_run)

    login = mega.check_login("mega-whoami")
    download = mega.download_link("mega-get", "https://example.invalid/file", Path("out"))

    assert login.logged_in is True
    assert download.exit_code == 0
    assert calls[0]["args"] == ["mega-whoami"]
    assert calls[1]["args"] == ["mega-get", "https://example.invalid/file", "out"]
    assert calls[0]["shell"] is False


def test_nonzero_login_and_output_truncation(monkeypatch) -> None:
    long_output = "x" * 5000

    def fake_run(args, shell, capture_output, text, timeout):
        return Completed(1, long_output, "")

    monkeypatch.setattr("subprocess.run", fake_run)

    login = mega.check_login("mega-whoami")

    assert login.logged_in is False
    assert login.exit_code == 1
    assert len(login.message) <= mega.OUTPUT_LIMIT
    assert login.message.endswith("...<truncated>")
