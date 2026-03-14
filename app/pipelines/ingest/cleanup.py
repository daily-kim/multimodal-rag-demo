from __future__ import annotations

from pathlib import Path
import shutil


def cleanup_temp_dir(path: str | Path) -> None:
    shutil.rmtree(Path(path), ignore_errors=True)
