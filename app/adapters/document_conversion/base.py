from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ConversionResult:
    output_path: Path
    page_count: int | None = None


class DocumentConverter(ABC):
    @abstractmethod
    def convert(self, source_path: str | Path, output_path: str | Path) -> ConversionResult:
        raise NotImplementedError

