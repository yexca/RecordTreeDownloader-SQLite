from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path

from recordtree.exceptions import ImportRowError, ValidationError
from recordtree.models import ImportRecord
from recordtree.normalizers import clean_text

from .parsers import parse_mega_json


class JsonImporter:
    extra_columns: tuple[str, ...] = ()

    def count_records(self, path: Path) -> int:
        root = _load_json_root(path)
        total = 0
        for author_item in root:
            if not isinstance(author_item, dict):
                total += 1
                continue
            records = author_item.get("records")
            total += len(records) if isinstance(records, list) else 1
        return total

    def iter_records(self, path: Path) -> Iterator[ImportRecord | ImportRowError]:
        root = _load_json_root(path)

        for author_index, author_item in enumerate(root, start=1):
            if not isinstance(author_item, dict):
                yield ImportRowError(
                    "json_author_invalid",
                    "JSON author item must be an object.",
                    row_number=author_index,
                    raw_value=author_item,
                )
                continue

            actor = clean_text(author_item.get("author"))
            records = author_item.get("records")
            if not isinstance(records, list):
                yield ImportRowError(
                    "json_records_missing",
                    "JSON author item is missing a records list.",
                    row_number=author_index,
                    raw_value=author_item,
                )
                continue

            for record_index, record_item in enumerate(records, start=1):
                row_number = _row_number(author_index, record_index)
                if not isinstance(record_item, dict):
                    yield ImportRowError(
                        "json_record_invalid",
                        "JSON record item must be an object.",
                        row_number=row_number,
                        raw_value=record_item,
                    )
                    continue
                if not isinstance(record_item.get("property"), list):
                    yield ImportRowError(
                        "mega_property_invalid",
                        "JSON record item is missing a property list.",
                        row_number=row_number,
                        raw_value=record_item,
                    )
                    continue
                try:
                    yield _parse_record(record_item, actor, row_number)
                except ImportRowError as error:
                    yield error


def _parse_record(record_item: dict[str, object], actor: str | None, row_number: int) -> ImportRecord:
    mega_payload = parse_mega_json(record_item, row_number)
    title = mega_payload.file_names or clean_text(record_item.get("FileNames"))
    return ImportRecord(
        source_type="json",
        actor_raw=actor or "",
        delivery_date=None,
        title=title or "",
        entry_date=None,
        note=None,
        upload_title=title or "",
        duplicate_search_raw=None,
        source_name=clean_text(record_item.get("source")) or "json",
        size_raw=mega_payload.formatted_size,
        size_bytes=mega_payload.total_bytes,
        mega_file_name=mega_payload.file_names,
        mega_total_bytes=mega_payload.total_bytes,
        mega_formatted_size=mega_payload.formatted_size,
        mega_json=json.dumps(record_item, ensure_ascii=False, sort_keys=True),
        source_row_number=row_number,
        links=mega_payload.links,
    )


def _row_number(author_index: int, record_index: int) -> int:
    return author_index * 100000 + record_index


def _load_json_root(path: Path) -> list[object]:
    try:
        root = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValidationError(f"JSON file could not be parsed: {error.msg}") from error
    if not isinstance(root, list):
        raise ValidationError("JSON root must be a list.")
    return root
