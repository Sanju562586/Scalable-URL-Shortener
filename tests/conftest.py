"""
Shared pytest fixtures for unit and integration tests.

Provides:
  • in-memory SQLite engine (no Postgres required for tests)
  • fakeredis server (no Redis required for tests)
  • TestClient backed by the above
  • Pre-created API key fixture
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
import fakeredis

from app.database import Base, get_db
from app.redis_client import get_redis
from app.main import create_app
from app.models.api_key import APIKey
from app.models.url import URL
import app.models  # noqa: F401 — registers all ORM models with metadata

# ── In-memory SQLite ──────────────────────────────────────────────────────────
TEST_DB_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once per test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db() -> Session:
    """
    Fresh transaction per test, rolled back after.

    SQLAlchemy 2.0-compatible pattern: we create a connection, begin a
    savepoint-based nested transaction, and bind a session to that
    connection so any ``commit()`` inside the test only flushes to the
    savepoint — the outer ``transaction.rollback()`` undoes everything.
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    # Create the session bound to this specific connection.
    # Using Session(bind=connection) is the only supported legacy path in 2.0.
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()



@pytest.fixture()
def fake_redis():
    """fakeredis server — in-process, no actual Redis needed."""
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server, decode_responses=True)
    yield client
    client.flushall()


@pytest.fixture()
def client(db: Session, fake_redis):
    """TestClient with overridden DB and Redis dependencies."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def api_key(db: Session) -> tuple[APIKey, str]:
    """
    Create and persist a test API key.

    Returns:
        (APIKey ORM object, raw_key string)
    """
    raw = APIKey.generate_raw_key()
    key_obj = APIKey(key_hash=APIKey.hash_key(raw), owner="test-owner", is_active=True)
    db.add(key_obj)
    db.commit()
    db.refresh(key_obj)
    return key_obj, raw


@pytest.fixture()
def auth_headers(api_key) -> dict:
    """HTTP headers dict with a valid X-API-Key."""
    _, raw = api_key
    return {"X-API-Key": raw}
