from fastapi.testclient import TestClient

from app.config import settings
from app.db import SessionLocal
from app.seed import seed_admin
from sqlalchemy import func, select

from app.models.user import User


def test_register_login_me_logout(client: TestClient) -> None:
    r = client.post(
        "/api/auth/register",
        json={"email": "a@example.com", "password": "Test@1234", "full_name": "A"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "user"
    r = client.post(
        "/api/auth/login",
        json={"email": "a@example.com", "password": "Test@1234"},
    )
    assert r.status_code == 200
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"
    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    payload = {"email": "dup@example.com", "password": "Test@1234", "full_name": "Dup"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 409


def test_login_invalid_credentials(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"email": "b@example.com", "password": "Test@1234", "full_name": "B"},
    )
    r = client.post(
        "/api/auth/login",
        json={"email": "b@example.com", "password": "wrong-password"},
    )
    assert r.status_code == 401


def test_seed_admin_idempotent() -> None:
    db = SessionLocal()
    try:
        seed_admin(db)
        db.commit()
        count_after_first = db.scalar(
            select(func.count()).select_from(User).where(User.email == settings.admin_email.lower())
        )
        assert count_after_first == 1
        admin = db.scalar(select(User).where(User.email == settings.admin_email.lower()))
        assert admin is not None
        assert admin.role == "admin"

        seed_admin(db)
        db.commit()
        count_after_second = db.scalar(
            select(func.count()).select_from(User).where(User.email == settings.admin_email.lower())
        )
        assert count_after_second == 1
    finally:
        db.close()
        with SessionLocal() as cleanup_db:
            admin = cleanup_db.scalar(
                select(User).where(User.email == settings.admin_email.lower())
            )
            if admin is not None:
                cleanup_db.delete(admin)
                cleanup_db.commit()
