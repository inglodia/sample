from uuid import UUID

from fastapi.testclient import TestClient


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
