from collections.abc import Generator
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import Base, get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models import *  # noqa: F401,F403,E402  # import models so Base.metadata is populated
from app.services import auth_service  # noqa: E402


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = Session()
    # Seed the admin user so auth tests can log in
    auth_service.ensure_admin_user(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session, request) -> Generator[TestClient, None, None]:
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = _get_test_db
    with TestClient(fastapi_app) as c:
        # Auto-login unless test is marked @pytest.mark.no_auth
        if not request.node.get_closest_marker("no_auth"):
            c.post("/api/auth/login", json={
                "username": "admin", "password": "BrainFlow@2026"
            })
        yield c
    fastapi_app.dependency_overrides.clear()
