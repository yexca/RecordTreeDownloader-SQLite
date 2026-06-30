from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .exceptions import ConfigError
from .path_templates import DEFAULT_DOWNLOAD_FOLDER_TEMPLATE, normalize_download_folder_template


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    downloads_dir: Path
    logs_dir: Path
    safety_margin_percent: int
    safety_margin_min_mb: int
    include_par2_by_default: bool
    folder_template: str
    mega_get: str
    mega_whoami: str
    mega_login: str
    mega_logout: str
    prefer_xlsx_metadata: bool


def default_config() -> dict[str, object]:
    return {
        "paths": {
            "database": "env/recordtree.sqlite3",
            "downloads": "downloads",
            "logs": "logs",
        },
        "download": {
            "safety_margin_percent": 5,
            "safety_margin_min_mb": 10240,
            "include_par2_by_default": False,
            "folder_template": DEFAULT_DOWNLOAD_FOLDER_TEMPLATE,
        },
        "mega": {
            "mega_get": "mega-get",
            "mega_whoami": "mega-whoami",
            "mega_login": "mega-login",
            "mega_logout": "mega-logout",
        },
        "import": {
            "prefer_xlsx_metadata": True,
        },
    }


def ensure_config(path: Path) -> Path:
    config_path = path.expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text(_format_default_config(), encoding="utf-8")
    return config_path.resolve()


def load_config(path: Path | None = None) -> AppConfig:
    config_path = (path or Path("env/config.toml")).expanduser()
    if not config_path.exists():
        raise ConfigError(f"Config file does not exist: {config_path}")

    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"Config file is invalid TOML: {config_path}") from error

    defaults = default_config()
    base_dir = Path.cwd().resolve()
    paths = _section(raw, "paths")
    download = _section(raw, "download")
    mega = _section(raw, "mega")
    import_config = _section(raw, "import")

    database = _string_value(paths, "database", defaults["paths"]["database"])
    downloads = _string_value(paths, "downloads", defaults["paths"]["downloads"])
    logs = _string_value(paths, "logs", defaults["paths"]["logs"])

    return AppConfig(
        database_path=resolve_path(base_dir, database),
        downloads_dir=resolve_path(base_dir, downloads),
        logs_dir=resolve_path(base_dir, logs),
        safety_margin_percent=_int_value(
            download,
            "safety_margin_percent",
            defaults["download"]["safety_margin_percent"],
        ),
        safety_margin_min_mb=_int_value(
            download,
            "safety_margin_min_mb",
            defaults["download"]["safety_margin_min_mb"],
        ),
        include_par2_by_default=_bool_value(
            download,
            "include_par2_by_default",
            defaults["download"]["include_par2_by_default"],
        ),
        folder_template=normalize_download_folder_template(
            _string_value(download, "folder_template", defaults["download"]["folder_template"])
        ),
        mega_get=_string_value(mega, "mega_get", defaults["mega"]["mega_get"]),
        mega_whoami=_string_value(mega, "mega_whoami", defaults["mega"]["mega_whoami"]),
        mega_login=_string_value(mega, "mega_login", defaults["mega"]["mega_login"]),
        mega_logout=_string_value(mega, "mega_logout", defaults["mega"]["mega_logout"]),
        prefer_xlsx_metadata=_bool_value(
            import_config,
            "prefer_xlsx_metadata",
            defaults["import"]["prefer_xlsx_metadata"],
        ),
    )


def resolve_path(base_dir: Path, configured_path: str) -> Path:
    candidate = Path(configured_path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()


def _format_default_config() -> str:
    return """[paths]
database = "env/recordtree.sqlite3"
downloads = "downloads"
logs = "logs"

[download]
safety_margin_percent = 5
safety_margin_min_mb = 10240
include_par2_by_default = false
folder_template = "{actor_safe_name}/{record_group_id}"

[mega]
mega_get = "mega-get"
mega_whoami = "mega-whoami"
mega_login = "mega-login"
mega_logout = "mega-logout"

[import]
prefer_xlsx_metadata = true
"""


def _section(config: dict[str, object], name: str) -> dict[str, object]:
    section = config.get(name, {})
    if not isinstance(section, dict):
        raise ConfigError(f"Config section [{name}] must be a table.")
    return section


def save_config(path: Path, config: AppConfig) -> Path:
    config_path = path.expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(_format_config(config), encoding="utf-8")
    return config_path.resolve()


def _string_value(section: dict[str, object], key: str, default: object) -> str:
    value = section.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Config value {key} must be a non-empty string.")
    return value


def _int_value(section: dict[str, object], key: str, default: object) -> int:
    value = section.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ConfigError(f"Config value {key} must be a non-negative integer.")
    return value


def _bool_value(section: dict[str, object], key: str, default: object) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"Config value {key} must be true or false.")
    return value


def _format_config(config: AppConfig) -> str:
    return f"""[paths]
database = "{_toml_string(_display_path(config.database_path))}"
downloads = "{_toml_string(_display_path(config.downloads_dir))}"
logs = "{_toml_string(_display_path(config.logs_dir))}"

[download]
safety_margin_percent = {config.safety_margin_percent}
safety_margin_min_mb = {config.safety_margin_min_mb}
include_par2_by_default = {_toml_bool(config.include_par2_by_default)}
folder_template = "{_toml_string(config.folder_template)}"

[mega]
mega_get = "{_toml_string(config.mega_get)}"
mega_whoami = "{_toml_string(config.mega_whoami)}"
mega_login = "{_toml_string(config.mega_login)}"
mega_logout = "{_toml_string(config.mega_logout)}"

[import]
prefer_xlsx_metadata = {_toml_bool(config.prefer_xlsx_metadata)}
"""


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path)


def _toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _toml_bool(value: bool) -> str:
    return "true" if value else "false"
