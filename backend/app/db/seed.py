"""Seed baseline reference data. Idempotent — safe to run repeatedly.

Run with:  uv run --directory backend python -m app.db.seed
"""

from app.db.models import Language
from app.db.session import SessionLocal

# Languages we offer. Spanish (Latin America) first.
LANGUAGES = [
    {"code": "es-LA", "name": "Latin American Spanish", "profile_key": "spanish"},
]


def seed_languages() -> None:
    with SessionLocal() as session:
        for data in LANGUAGES:
            # session.get looks a row up by primary key; insert only if missing.
            if session.get(Language, data["code"]) is None:
                session.add(Language(**data))
        session.commit()


# This block runs only when the file is executed directly (python -m app.db.seed),
# not when it's imported. (Like `if (require.main === module)` in Node.)
if __name__ == "__main__":
    seed_languages()
    print("Seeded languages.")
