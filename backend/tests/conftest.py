from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.db import engine, get_db
from app.deps import hash_password
from app.main import app
from app.models.user import User


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestingSessionLocal()

    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess: Session, trans) -> None:
        parent = trans._parent
        if trans.nested and parent is not None and not parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _authed_client(db_session: Session, email: str, password: str, role: str) -> TestClient:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    user = User(
        email=email.strip().lower(),
        password_hash=hash_password(password),
        full_name="Test",
        role=role,
    )
    db_session.add(user)
    db_session.flush()
    test_client = TestClient(app)
    test_client.post("/api/auth/login", json={"email": email, "password": password})
    return test_client


@pytest.fixture
def admin_client(db_session: Session) -> Generator[TestClient, None, None]:
    c = _authed_client(db_session, "admin-test@example.com", "Test@1234", "admin")
    try:
        yield c
    finally:
        c.close()
        app.dependency_overrides.clear()


@pytest.fixture
def user_client(db_session: Session) -> Generator[TestClient, None, None]:
    c = _authed_client(db_session, "user-test@example.com", "Test@1234", "user")
    try:
        yield c
    finally:
        c.close()
        app.dependency_overrides.clear()


@pytest.fixture
def registered_user_id(db_session: Session) -> UUID:
    user = User(
        email="promote-me@example.com",
        password_hash=hash_password("Test@1234"),
        full_name="Promote",
        role="user",
    )
    db_session.add(user)
    db_session.flush()
    return user.id
