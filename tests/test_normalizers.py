from __future__ import annotations

from datetime import date, datetime

import pytest

from recordtree.exceptions import ValidationError
from recordtree.models import ImportRecord, LinkItem
from recordtree.normalizers import (
    build_link_set_hash,
    build_source_key,
    clean_text,
    normalize_date,
    normalize_file_type,
    normalize_search_text,
)


def _record(*, title: str = "Title", source: str = "Source", delivery_date: str | None = "2026-01-02") -> ImportRecord:
    return ImportRecord(
        source_type="xlsx",
        actor_raw=" Actor ",
        delivery_date=delivery_date,
        title=title,
        entry_date="2026-01-03",
        note=None,
        upload_title="Upload",
        duplicate_search_raw=None,
        source_name=source,
        size_raw=None,
        size_bytes=3,
        mega_file_name="bundle",
        mega_total_bytes=3,
        mega_formatted_size=None,
        mega_json="{}",
        source_row_number=2,
        links=[],
    )


def test_text_file_type_and_date_normalization() -> None:
    assert clean_text(None) is None
    assert clean_text("   ") is None
    assert clean_text("  value  ") == "value"
    assert normalize_search_text("  MIXED  ") == "mixed"
    assert normalize_file_type("mp4") == ".mp4"
    assert normalize_file_type(".MP4") == ".mp4"
    assert normalize_date(datetime(2026, 1, 2, 3, 4, 5)) == "2026-01-02"
    assert normalize_date(date(2026, 1, 2)) == "2026-01-02"
    assert normalize_date("2026-01-02") == "2026-01-02"
    assert normalize_date("") is None


def test_invalid_date_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        normalize_date("not-a-date")


def test_source_key_and_link_set_hash_are_stable_and_sensitive() -> None:
    assert build_source_key(_record()) == build_source_key(_record())
    assert build_source_key(_record(title="Changed")) != build_source_key(_record())
    assert build_source_key(_record(source="Changed")) != build_source_key(_record())
    assert build_source_key(_record(delivery_date="2026-02-02")) != build_source_key(_record())

    links = [
        LinkItem(1, "https://example.invalid/1", "mp4", 1, "1 B"),
        LinkItem(2, "https://example.invalid/2", "m4a", 2, "2 B"),
    ]
    reordered = [
        LinkItem(2, "https://example.invalid/2", "m4a", 2, "2 B"),
        LinkItem(1, "https://example.invalid/1", "mp4", 1, "1 B"),
    ]
    assert build_link_set_hash(links) == build_link_set_hash(list(links))
    assert build_link_set_hash(links) != build_link_set_hash(reordered)
