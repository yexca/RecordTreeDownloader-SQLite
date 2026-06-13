class RecordTreeError(Exception):
    """Base class for user-facing RecordTree errors."""


class ConfigError(RecordTreeError):
    """Raised when configuration is missing or invalid."""


class ValidationError(RecordTreeError):
    """Raised when user input or imported data is invalid."""


class NotFoundError(RecordTreeError):
    """Raised when a requested record cannot be found."""


class NotImplementedFeatureError(RecordTreeError):
    """Raised by placeholder commands before implementation lands."""
