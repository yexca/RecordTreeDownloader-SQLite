from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re


_UNITS = {
    "B": 1,
    "KB": 1024,
    "MB": 1024**2,
    "GB": 1024**3,
    "TB": 1024**4,
}


def parse_size_text(value: object | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = str(value).strip()
    if not text:
        return None
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([kmgt]?b)?", text, re.IGNORECASE)
    if not match:
        return None
    try:
        amount = Decimal(match.group(1))
    except InvalidOperation:
        return None
    unit = (match.group(2) or "B").upper()
    multiplier = _UNITS.get(unit)
    if multiplier is None:
        return None
    return int(amount * multiplier)


def calculate_margin(selected_bytes: int, percent: int, min_mb: int) -> int:
    percent_margin = selected_bytes * percent // 100
    min_margin = min_mb * 1024 * 1024
    return max(percent_margin, min_margin)


def calculate_required_bytes(selected_bytes: int, percent: int, min_mb: int) -> int:
    return selected_bytes + calculate_margin(selected_bytes, percent, min_mb)


def format_bytes(value: int | None) -> str:
    if value is None:
        return ""
    amount = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if amount < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(amount)} B"
            return f"{amount:.2f} {unit}"
        amount /= 1024
    return f"{amount:.2f} TB"
