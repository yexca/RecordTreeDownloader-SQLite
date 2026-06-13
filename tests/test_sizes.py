from __future__ import annotations

from recordtree.sizes import calculate_margin, calculate_required_bytes, parse_size_text


def test_parse_size_text_examples() -> None:
    assert parse_size_text("894.12 MB") == int(894.12 * 1024 * 1024)
    assert parse_size_text("13.53 GB") == int(13.53 * 1024 * 1024 * 1024)
    assert parse_size_text("0 B") == 0
    assert parse_size_text("1024 KB") == 1024 * 1024
    assert parse_size_text("malformed text") is None
    assert parse_size_text(None) is None


def test_safety_margin_uses_larger_of_percent_and_minimum() -> None:
    minimum = 512 * 1024 * 1024
    assert calculate_margin(100 * 1024 * 1024, 5, 512) == minimum
    assert calculate_margin(20 * 1024 * 1024 * 1024, 5, 512) == 1024 * 1024 * 1024
    assert calculate_required_bytes(100, 5, 512) == 100 + minimum
