from __future__ import annotations

from app.config import get_settings
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_engine


def main() -> None:
    settings = get_settings()
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    print(f"initialized database at {settings.database_url}")


if __name__ == "__main__":
    main()

