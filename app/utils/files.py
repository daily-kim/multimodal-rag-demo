from __future__ import annotations

import re
from pathlib import Path


_INVALID_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    cleaned = _INVALID_FILENAME_CHARS.sub("_", name)
    return cleaned or "upload.bin"


def file_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def slugify(value: str) -> str:
    normalized = _INVALID_FILENAME_CHARS.sub("-", value.strip().lower())
    normalized = normalized.strip("-")
    return normalized or "default-space"

