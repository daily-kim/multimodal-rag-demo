from __future__ import annotations

from pathlib import Path

from PIL import Image


class ThumbnailGenerator:
    def create(self, source_image_path: str | Path, output_path: str | Path, *, size: tuple[int, int] = (320, 320)) -> Path:
        source = Path(source_image_path)
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        image = Image.open(source)
        image.thumbnail(size)
        image.convert("RGB").save(target, format="JPEG", quality=85)
        return target

