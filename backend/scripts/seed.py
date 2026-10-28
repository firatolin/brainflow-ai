"""Run: python -m scripts.seed [--no-reset]"""
from __future__ import annotations

import sys

from app.core.database import SessionLocal
from app.services.seed import seed_database


def main() -> None:
    reset = "--no-reset" not in sys.argv
    db = SessionLocal()
    try:
        summary = seed_database(db, reset=reset)
        print("Seed complete:")
        for k, v in summary.items():
            print(f"  {k}: {v}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
