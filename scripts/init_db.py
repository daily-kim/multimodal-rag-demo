from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import get_settings


def main() -> None:
    settings = get_settings()

    config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    command.upgrade(config, "head")

    print(f"initialized database schema at {settings.database_url}")


if __name__ == "__main__":
    main()
