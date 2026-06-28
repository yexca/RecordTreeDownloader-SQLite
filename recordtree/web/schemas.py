from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class DownloadPlanRequest(BaseModel):
    include_par2: bool = False
    types: str | list[str] | None = None
    output: str | None = None
    only_undownloaded: bool = False

    def types_text(self) -> str | None:
        if self.types is None:
            return None
        if isinstance(self.types, str):
            return self.types
        return ",".join(self.types)

    def output_path(self) -> Path | None:
        if self.output is None or not self.output.strip():
            return None
        return Path(self.output)

