from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass(slots=True)
class PageSlice:
    items: list
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        return max(1, ceil(self.total / max(self.page_size, 1)))

