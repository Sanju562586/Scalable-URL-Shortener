"""
SQLAlchemy engine, session factory, and declarative base.
All models import Base from here so Alembic can auto-detect them.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator

from app.config import get_settings

logger = logging.getLogger("url_shortener.database")
settings = get_settings()

# psycopg3 (psycopg[binary]) does not support pool_size/max_overflow
# on the sync driver. Use NullPool to avoid "Can't reload..." errors.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # test connections before using (handles stale connections)
    poolclass=NullPool,   # required for psycopg3 sync driver compatibility
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and guarantees cleanup.
    Rolls back on any unhandled exception to prevent dirty state.

    Usage:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        logger.exception("Unhandled exception in DB session — rolling back")
        db.rollback()
        raise
    finally:
        db.close()
