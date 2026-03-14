from __future__ import annotations

import base64
import mimetypes
from pathlib import Path


def file_to_data_url(path: str | Path) -> str:
    resolved = Path(path)
    mime_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
    payload = base64.b64encode(resolved.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{payload}"

