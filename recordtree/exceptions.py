class RecordTreeError(Exception):
    """Base class for user-facing RecordTree errors."""


class ConfigError(RecordTreeError):
    """Raised when configuration is missing or invalid."""


class ValidationError(RecordTreeError):
    """Raised when user input or imported data is invalid."""


class ImportRowError(RecordTreeError):
    """Raised for a single bad imported row while the import can continue."""

    def __init__(
        self,
        error_type: str,
        message: str,
        *,
        row_number: int | None = None,
        source_key: str | None = None,
        raw_value: object | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.row_number = row_number
        self.source_key = source_key
        self.raw_value = None if raw_value is None else str(raw_value)


class NotFoundError(RecordTreeError):
    """Raised when a requested record cannot be found."""


class NotImplementedFeatureError(RecordTreeError):
    """Raised by placeholder commands before implementation lands."""
