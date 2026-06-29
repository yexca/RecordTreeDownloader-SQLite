from __future__ import annotations

import io
from pathlib import Path
import subprocess

from recordtree import mega


class Completed:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_check_login_and_download_use_subprocess_lists(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(args, shell, capture_output, text, encoding, errors, timeout):
        calls.append(
            {
                "args": args,
                "shell": shell,
                "capture_output": capture_output,
                "text": text,
                "encoding": encoding,
                "errors": errors,
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
    assert calls[0]["encoding"] == "utf-8"
    assert calls[0]["errors"] == "replace"
    assert calls[0]["timeout"] == mega.COMMAND_TIMEOUT_SECONDS
    assert calls[1]["timeout"] is None


def test_nonzero_login_and_output_truncation(monkeypatch) -> None:
    long_output = "x" * 5000

    def fake_run(args, shell, capture_output, text, encoding, errors, timeout):
        return Completed(1, long_output, "")

    monkeypatch.setattr("subprocess.run", fake_run)

    login = mega.check_login("mega-whoami")

    assert login.logged_in is False
    assert login.exit_code == 1
    assert len(login.message) <= mega.OUTPUT_LIMIT
    assert login.message.endswith("...<truncated>")


def test_download_link_streams_process_output(monkeypatch, tmp_path: Path) -> None:
    calls = []
    output_chunks = []

    class FakeProcess:
        def __init__(self, args, **kwargs):
            calls.append((args, kwargs))
            self.stdout = io.StringIO("downloading\r100%\n")
            self.stderr = io.StringIO("warning\n")

        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", FakeProcess)

    result = mega.download_link(
        "mega-get",
        "https://example.invalid/file",
        tmp_path,
        output_callback=output_chunks.append,
    )

    assert result.exit_code == 0
    assert result.stdout == "downloading\r100%\n"
    assert result.stderr == "warning\n"
    streamed_output = "".join(output_chunks)
    assert "downloading\r100%\n" in streamed_output
    assert "warning\n" in streamed_output
    assert calls == [
        (
            ["mega-get", "https://example.invalid/file", str(tmp_path)],
            {
                "shell": False,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
                "bufsize": 1,
            },
        )
    ]


def test_login_uses_megacmd_non_interactive_arguments(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(args, shell, capture_output, text, encoding, errors, timeout):
        calls.append(
            {
                "args": args,
                "shell": shell,
                "capture_output": capture_output,
                "text": text,
                "encoding": encoding,
                "errors": errors,
                "timeout": timeout,
            }
        )
        return Completed(0, "logged in", "")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = mega.login_account("mega-login", "user@example.com", "secret", "123456")

    assert result.exit_code == 0
    assert calls[0]["args"] == ["mega-login", "user@example.com", "secret", "--auth-code=123456"]
    assert calls[0]["shell"] is False


def test_logout_runs_mega_logout(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return Completed(0, "logged out", "")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = mega.logout_account("mega-logout")

    assert result.exit_code == 0
    assert calls == [["mega-logout"]]
