import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Where to find the database.
# Default = the local dev DB that docker-compose publishes on the host at port 5433.
# Inside Docker, the `api` container overrides this with DATABASE_URL pointing at the
# internal `db` service (db:5432). Format:
#   postgresql+psycopg://<user>:<password>@<host>:<port>/<database>
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://storygen:storygen@localhost:5433/storygen",
)

# The engine owns the pool of connections to Postgres. Create it once, reuse everywhere.
# pool_pre_ping checks a connection is still alive before handing it out (avoids stale ones).
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# A "session" is one unit of work / conversation with the DB. Call SessionLocal() to make one.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# Parent class for our table models (used starting in the next step).
class Base(DeclarativeBase):
    pass
