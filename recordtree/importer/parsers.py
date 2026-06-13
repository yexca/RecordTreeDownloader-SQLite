from __future__ import annotations

from dataclasses import dataclass
import json

from recordtree.exceptions import ImportRowError
from recordtree.models import LinkItem
from recordtree.normalizers import clean_text, normalize_file_type


@dataclass(frozen=True)
class MegaPayload:
    file_names: str | None
    total_bytes: int | None
    formatted_size: str | None
    links: list[LinkItem]


def parse_mega_json(raw: object, row_number: int | None = None) -> MegaPayload:
    if isinstance(raw, dict):
        root = raw
        text = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    else:
        text = clean_text(raw)
        if text is None:
            raise ImportRowError(
                "mega_json_parse_error",
                "MEGA JSON is empty.",
                row_number=row_number,
                raw_value=raw,
            )
        try:
            root = json.loads(text)
        except json.JSONDecodeError as error:
            raise ImportRowError(
                "mega_json_parse_error",
                f"MEGA JSON could not be parsed: {error.msg}",
                row_number=row_number,
                raw_value=text,
            ) from error
    if not isinstance(root, dict):
        raise ImportRowError(
            "mega_json_invalid_root",
            "MEGA JSON root must be an object.",
            row_number=row_number,
            raw_value=text,
        )
    property_items = root.get("property")
    if not isinstance(property_items, list):
        raise ImportRowError(
            "mega_property_invalid",
            "MEGA property must be a list.",
            row_number=row_number,
            raw_value=text,
        )
    if not property_items:
        raise ImportRowError(
            "mega_property_empty",
            "MEGA property list is empty.",
            row_number=row_number,
            raw_value=text,
        )

    links = [_parse_link_item(item, index + 1, row_number) for index, item in enumerate(property_items)]
    return MegaPayload(
        file_names=clean_text(root.get("FileNames")),
        total_bytes=_optional_int(root.get("total"), "mega_size_invalid", row_number, root.get("total")),
        formatted_size=clean_text(root.get("FormattedSize")),
        links=links,
    )


def _parse_link_item(item: object, order: int, row_number: int | None) -> LinkItem:
    if not isinstance(item, dict):
        raise ImportRowError(
            "mega_property_invalid",
            "Each MEGA property item must be an object.",
            row_number=row_number,
            raw_value=item,
        )
    link = clean_text(item.get("Link"))
    if link is None:
        raise ImportRowError(
            "mega_link_missing",
            "MEGA link is missing.",
            row_number=row_number,
            raw_value=item,
        )
    size = _required_int(item.get("Size"), "mega_size_invalid", row_number)
    return LinkItem(
        link_order=order,
        mega_url=link,
        file_type=normalize_file_type(item.get("Type")),
        size_bytes=size,
        formatted_size=clean_text(item.get("FormattedSize")),
    )


def _required_int(value: object, error_type: str, row_number: int | None) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError
        return int(value)
    except (TypeError, ValueError) as error:
        raise ImportRowError(
            error_type,
            "MEGA size must be an integer.",
            row_number=row_number,
            raw_value=value,
        ) from error


def _optional_int(
    value: object,
    error_type: str,
    row_number: int | None,
    raw_value: object,
) -> int | None:
    if clean_text(value) is None:
        return None
    return _required_int(value, error_type, row_number)
