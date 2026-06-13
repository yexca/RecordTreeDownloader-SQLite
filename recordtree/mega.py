from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from .exceptions import ExternalToolError
from .models import MegaCommandResult, MegaLoginStatus


OUTPUT_LIMIT = 4000
COMMAND_TIMEOUT_SECONDS = 30


def resolve_executable(configured: str) -> str:
    resolved = shutil.which(configured)
    if resolved is not None:
        return resolved
    candidate = Path(configured).expanduser()
    if candidate.is_file():
        return str(candidate.resolve())
    raise ExternalToolError(f"MEGAcmd executable not found: {configured}")


def check_login(mega_whoami: str) -> MegaLoginStatus:
    result = _run_command([mega_whoami])
    message = _combine_output(result)
    return MegaLoginStatus(
        logged_in=result.exit_code == 0,
        exit_code=result.exit_code,
        message=message,
    )


def download_link(mega_get: str, mega_url: str, output_dir: Path) -> MegaCommandResult:
    return _run_command([mega_get, mega_url, str(output_dir)])


def _run_command(args: list[str]) -> MegaCommandResult:
    try:
        completed = subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
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


def _combine_output(result: MegaCommandResult) -> str:
    text = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return text or f"exit_code={result.exit_code}"


def _truncate(value: str) -> str:
    if len(value) <= OUTPUT_LIMIT:
        return value
    return value[: OUTPUT_LIMIT - 15] + "...<truncated>"
