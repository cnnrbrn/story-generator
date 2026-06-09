from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# The database address comes from settings (env var DATABASE_URL, else the local-dev
# default). Inside Docker the `api` container sets DATABASE_URL to reach the db service.
DATABASE_URL = settings.database_url

# The engine owns the pool of connections to Postgres. Create it once, reuse everywhere.
# pool_pre_ping checks a connection is still alive before handing it out (avoids stale ones).
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# A "session" is one unit of work / conversation with the DB. Call SessionLocal() to make one.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# Parent class for our table models.
class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a session and always closes it after the request.

    Used as `db: Session = Depends(get_db)` in route handlers.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
