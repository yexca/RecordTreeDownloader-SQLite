from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path

from .exceptions import ValidationError


DEFAULT_DOWNLOAD_FOLDER_TEMPLATE = "{actor_safe_name}/{record_group_id}"

_TOKEN_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")
_UNSAFE_SEGMENT_CHARS = re.compile(r'[<>:"\\|?*\x00-\x1f]')
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


@dataclass(frozen=True)
class DownloadTemplateContext:
    record_group_id: int
    actor: str
    title: str
    source: str
    source_key: str
    delivery_date: str | None
    entry_date: str | None


def allowed_download_template_variables() -> dict[str, str]:
    return {
        "actor_safe_name": "Actor name cleaned for folder names",
        "actor": "Actor name cleaned for folder names",
        "record_group_id": "Record group id",
        "source": "Source/platform name cleaned for folder names",
        "source_key": "Stable source key",
        "title_safe": "Title cleaned for folder names",
        "title": "Title cleaned for folder names",
        "delivery_date": "Delivery date",
        "entry_date": "Entry date",
    }


def normalize_download_folder_template(template: str) -> str:
    text = template.strip().replace("\\", "/")
    text = re.sub(r"/{2,}", "/", text)
    text = text.strip("/")
    if not text:
        raise ValidationError("Download folder template must not be empty.")
    if Path(text).is_absolute() or re.match(r"^[A-Za-z]:", text):
        raise ValidationError("Download folder template must be relative to the downloads directory.")

    parts = [part.strip() for part in text.split("/") if part.strip()]
    if any(part == ".." for part in parts):
        raise ValidationError("Download folder template must not contain '..'.")
    unknown = sorted({match.group(1) for match in _TOKEN_RE.finditer(text)} - set(allowed_download_template_variables()))
    if unknown:
        raise ValidationError("Unknown download folder template variable(s): " + ", ".join(f"{{{name}}}" for name in unknown))
    return "/".join(parts)


def render_download_folder_template(template: str, context: DownloadTemplateContext) -> Path:
    normalized = normalize_download_folder_template(template)
    values = _template_values(context)
    rendered_parts: list[str] = []
    for part in normalized.split("/"):
        rendered = part
        for token in _TOKEN_RE.finditer(part):
            name = token.group(1)
            rendered = rendered.replace(token.group(0), values[name])
        cleaned = safe_path_segment(rendered)
        if cleaned:
            rendered_parts.append(cleaned)
    if not rendered_parts:
        raise ValidationError("Download folder template produced an empty path.")
    return Path(*rendered_parts)


def safe_path_segment(value: object | None, fallback: str = "Unknown") -> str:
    text = str(value or "").strip()
    text = text.replace("/", " ").replace("\\", " ")
    text = _UNSAFE_SEGMENT_CHARS.sub("_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    if not text:
        text = fallback
    if text.upper() in _WINDOWS_RESERVED_NAMES:
        text = f"{text}_"
    return text


def _template_values(context: DownloadTemplateContext) -> dict[str, str]:
    actor = safe_path_segment(context.actor, fallback="Unknown Actor")
    title = safe_path_segment(context.title, fallback=f"Record {context.record_group_id}")
    source = safe_path_segment(context.source, fallback="Unknown Source")
    return {
        "actor_safe_name": actor,
        "actor": actor,
        "record_group_id": str(context.record_group_id),
        "source": source,
        "source_key": safe_path_segment(context.source_key, fallback=str(context.record_group_id)),
        "title_safe": title,
        "title": title,
        "delivery_date": safe_path_segment(context.delivery_date, fallback="undated"),
        "entry_date": safe_path_segment(context.entry_date, fallback="undated"),
    }
