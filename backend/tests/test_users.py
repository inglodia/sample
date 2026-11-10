from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


def test_users_admin_only(
    client: TestClient, admin_client: TestClient, user_client: TestClient
) -> None:
    assert user_client.get("/api/users").status_code == 403
    assert admin_client.get("/api/users").status_code == 200


def test_promote_user(admin_client: TestClient, registered_user_id: UUID) -> None:
    r = admin_client.patch(
        f"/api/users/{registered_user_id}/role", json={"role": "admin"}
    )
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_patch_role_sets_updated_at(
    admin_client: TestClient,
    db_session: Session,
    registered_user_id: UUID,
) -> None:
    user = db_session.get(User, registered_user_id)
    assert user is not None
    before = user.updated_at
    r = admin_client.patch(
        f"/api/users/{registered_user_id}/role", json={"role": "admin"}
    )
    assert r.status_code == 200
    db_session.refresh(user)
    assert user.updated_at is not None
    if before is not None:
        assert user.updated_at >= before - timedelta(seconds=1)
