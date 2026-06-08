import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

# env.py lives in backend/alembic/, so ".." is backend/ — add it so "app" is importable.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import DATABASE_URL, Base  # noqa: E402
from app.db import models  # noqa: E402,F401  (import registers tables on Base.metadata)

# Alembic config (reads logging settings from alembic.ini).
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate compares this metadata against the live database.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL without a live DB connection (alembic upgrade --sql)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against the live database."""
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
