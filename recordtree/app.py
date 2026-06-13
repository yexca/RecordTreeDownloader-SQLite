from __future__ import annotations

from pathlib import Path

from .exceptions import NotImplementedFeatureError
from .models import InitResult


class RecordTreeApp:
    """Application service layer for CLI use cases."""

    def init(self) -> InitResult:
        raise NotImplementedFeatureError("Database initialization is not implemented yet.")

    def doctor(self) -> None:
        raise NotImplementedFeatureError("Doctor checks are not implemented yet.")

    def import_file(self, path: Path) -> None:
        raise NotImplementedFeatureError(f"Import is not implemented yet: {path}")

    def stats(self) -> None:
        raise NotImplementedFeatureError("Stats are not implemented yet.")
