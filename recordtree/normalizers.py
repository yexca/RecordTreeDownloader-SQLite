from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import math

from .exceptions import ValidationError
from .models import ImportRecord, LinkItem


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text or None


def normalize_search_text(value: object) -> str:
    cleaned = clean_text(value)
    return "" if cleaned is None else cleaned.casefold()


def normalize_date(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Excel serial dates are intentionally not guessed here; openpyxl usually
        # returns typed date objects for date-formatted cells.
        if isinstance(value, float) and math.isnan(value):
            return None
        value = int(value) if float(value).is_integer() else value
    text = clean_text(value)
    if text is None:
        return None

    normalized = text.replace("/", "-").replace(".", "-")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(normalized, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError as error:
        raise ValidationError(f"Invalid date value: {text}") from error


def normalize_file_type(value: object) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    normalized = text.casefold()
    return normalized if normalized.startswith(".") else f".{normalized}"


def build_source_key(record: ImportRecord) -> str:
    payload = {
        "actor_raw": normalize_search_text(record.actor_raw),
        "delivery_date": record.delivery_date,
        "title": normalize_search_text(record.title),
        "entry_date": record.entry_date,
        "upload_title": normalize_search_text(record.upload_title),
        "source_name": normalize_search_text(record.source_name),
    }
    return _hash_payload(payload)


def build_link_content_hash(link: LinkItem) -> str:
    payload = {
        "mega_url": clean_text(link.mega_url),
        "file_type": normalize_file_type(link.file_type),
        "size_bytes": _safe_int(link.size_bytes),
        "formatted_size": clean_text(link.formatted_size),
    }
    return _hash_payload(payload)


def build_link_set_hash(links: Iterable[LinkItem]) -> str:
    payload = [
        {
            "link_order": link.link_order,
            "mega_url": clean_text(link.mega_url),
            "file_type": normalize_file_type(link.file_type),
            "size_bytes": _safe_int(link.size_bytes),
            "formatted_size": clean_text(link.formatted_size),
        }
        for link in links
    ]
    return _hash_payload(payload)


def _hash_payload(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_int(value: object) -> int:
    if isinstance(value, bool):
        raise ValidationError("Boolean values are not valid integers.")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, Decimal):
        return int(value)
    return int(str(value).strip())
