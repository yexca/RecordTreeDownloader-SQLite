from __future__ import annotations

import json

import pytest

from recordtree.exceptions import ImportRowError
from recordtree.importer.parsers import parse_mega_json


def test_parse_mega_json_valid_payload_and_numeric_string_size() -> None:
    payload = {
        "FileNames": "bundle",
        "total": "123",
        "FormattedSize": "123 B",
        "property": [
            {
                "Link": "https://example.invalid/file",
                "Size": "123",
                "FormattedSize": "123 B",
                "Type": "MP4",
            }
        ],
    }

    parsed = parse_mega_json(json.dumps(payload), row_number=7)

    assert parsed.file_names == "bundle"
    assert parsed.total_bytes == 123
    assert parsed.formatted_size == "123 B"
    assert len(parsed.links) == 1
    assert parsed.links[0].mega_url == "https://example.invalid/file"
    assert parsed.links[0].size_bytes == 123
    assert parsed.links[0].file_type == ".mp4"


@pytest.mark.parametrize(
    ("raw", "error_type"),
    [
        ([], "mega_json_invalid_root"),
        ({}, "mega_property_invalid"),
        ({"property": {}}, "mega_property_invalid"),
        ({"property": [{"Size": 1, "Type": "mp4"}]}, "mega_link_missing"),
        ({"property": [{"Link": "https://example.invalid/file", "Size": "bad", "Type": "mp4"}]}, "mega_size_invalid"),
    ],
)
def test_parse_mega_json_reports_invalid_shapes(raw: object, error_type: str) -> None:
    with pytest.raises(ImportRowError) as error:
        parse_mega_json(raw, row_number=3)

    assert error.value.error_type == error_type


def test_parse_mega_json_allows_missing_type() -> None:
    parsed = parse_mega_json({"property": [{"Link": "https://example.invalid/file", "Size": 1}]})

    assert parsed.links[0].file_type is None
