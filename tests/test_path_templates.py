from __future__ import annotations

import pytest

from recordtree.exceptions import ValidationError
from recordtree.path_templates import (
    DownloadTemplateContext,
    normalize_download_folder_template,
    render_download_folder_template,
    safe_path_segment,
)


def _context() -> DownloadTemplateContext:
    return DownloadTemplateContext(
        record_group_id=12,
        actor='A/B: Actor',
        title='Title * "One"',
        source="Source",
        source_key="abc123",
        delivery_date="2026-01-02",
        entry_date=None,
    )


def test_template_is_relative_and_trims_slashes() -> None:
    assert normalize_download_folder_template("/{actor_safe_name}//{record_group_id}/") == "{actor_safe_name}/{record_group_id}"


def test_render_template_sanitizes_variable_segments() -> None:
    assert render_download_folder_template("{actor_safe_name}/{record_group_id}/{title_safe}", _context()).as_posix() == (
        "A B_ Actor/12/Title _ _One_"
    )


def test_template_rejects_drive_parent_and_unknown_variables() -> None:
    for template in ("C:/tmp/{record_group_id}", "../{record_group_id}", "{missing}/{record_group_id}"):
        with pytest.raises(ValidationError):
            normalize_download_folder_template(template)


def test_safe_segment_handles_windows_reserved_names() -> None:
    assert safe_path_segment("CON") == "CON_"
    assert safe_path_segment(" . ") == "Unknown"
