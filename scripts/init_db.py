"""Inicializa la base de datos (crea el esquema).

Uso:  python -m scripts.init_db
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from core.database import init_db  # noqa: E402


def main() -> None:
    init_db()
    print(f"✅ Base de datos inicializada en: {settings.DB_PATH}")


if __name__ == "__main__":
    main()
