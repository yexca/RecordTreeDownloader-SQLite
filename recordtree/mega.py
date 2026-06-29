from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shutil
import subprocess
import threading

from .exceptions import ExternalToolError
from .models import MegaCommandResult, MegaLoginStatus


OUTPUT_LIMIT = 4000
COMMAND_TIMEOUT_SECONDS = 30
MEGACMD_OUTPUT_ENCODING = "utf-8"


def resolve_executable(configured: str) -> str:
    resolved = shutil.which(configured)
    if resolved is not None:
        return resolved
    candidate = Path(configured).expanduser()
    if candidate.is_file():
        return str(candidate.resolve())
    raise ExternalToolError(f"MEGAcmd executable not found: {configured}")


def check_login(mega_whoami: str) -> MegaLoginStatus:
    result = _run_command([mega_whoami], timeout=COMMAND_TIMEOUT_SECONDS)
    message = _combine_output(result)
    return MegaLoginStatus(
        logged_in=result.exit_code == 0,
        exit_code=result.exit_code,
        message=message,
    )


def login_account(
    mega_login: str,
    email: str,
    password: str,
    auth_code: str | None = None,
) -> MegaCommandResult:
    args = [mega_login, email, password]
    if auth_code:
        args.append(f"--auth-code={auth_code}")
    return _run_command(args, timeout=COMMAND_TIMEOUT_SECONDS)


def logout_account(mega_logout: str) -> MegaCommandResult:
    return _run_command([mega_logout], timeout=COMMAND_TIMEOUT_SECONDS)


def download_link(
    mega_get: str,
    mega_url: str,
    output_dir: Path,
    output_callback: Callable[[str], None] | None = None,
) -> MegaCommandResult:
    args = [mega_get, mega_url, str(output_dir)]
    if output_callback is not None:
        return _run_command_streaming(args, output_callback)
    return _run_command(args, timeout=None)


def _run_command(args: list[str], timeout: int | None) -> MegaCommandResult:
    try:
        completed = subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            encoding=MEGACMD_OUTPUT_ENCODING,
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        return MegaCommandResult(
            exit_code=1,
            stdout=_truncate(error.stdout or ""),
            stderr=f"Command timed out after {COMMAND_TIMEOUT_SECONDS} seconds.",
        )
    except OSError as error:
        return MegaCommandResult(exit_code=1, stdout="", stderr=_truncate(str(error)))
    return MegaCommandResult(
        exit_code=int(completed.returncode),
        stdout=_truncate(completed.stdout or ""),
        stderr=_truncate(completed.stderr or ""),
    )


def _run_command_streaming(args: list[str], output_callback: Callable[[str], None]) -> MegaCommandResult:
    try:
        process = subprocess.Popen(
            args,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding=MEGACMD_OUTPUT_ENCODING,
            errors="replace",
            bufsize=1,
        )
    except OSError as error:
        return MegaCommandResult(exit_code=1, stdout="", stderr=_truncate(str(error)))

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    stdout_thread = threading.Thread(
        target=_read_stream,
        args=(process.stdout, stdout_parts, output_callback),
    )
    stderr_thread = threading.Thread(
        target=_read_stream,
        args=(process.stderr, stderr_parts, output_callback),
    )
    stdout_thread.start()
    stderr_thread.start()
    exit_code = process.wait()
    stdout_thread.join()
    stderr_thread.join()
    return MegaCommandResult(
        exit_code=int(exit_code),
        stdout=_truncate("".join(stdout_parts)),
        stderr=_truncate("".join(stderr_parts)),
    )


def _read_stream(
    stream,
    output_parts: list[str],
    output_callback: Callable[[str], None],
) -> None:
    if stream is None:
        return
    with stream:
        while True:
            chunk = stream.read(1)
            if chunk == "":
                break
            output_parts.append(chunk)
            output_callback(chunk)


def _combine_output(result: MegaCommandResult) -> str:
    text = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return text or f"exit_code={result.exit_code}"


def _truncate(value: str) -> str:
    if len(value) <= OUTPUT_LIMIT:
        return value
    return value[: OUTPUT_LIMIT - 15] + "...<truncated>"
