from fastapi.testclient import TestClient


def test_dashboard_stats(admin_client: TestClient) -> None:
    r = admin_client.get("/api/dashboard/stats")
    assert r.status_code == 200
    body = r.json()
    assert "total_users" in body and "signups_by_day" in body


def test_dashboard_stats_requires_auth(client: TestClient) -> None:
    assert client.get("/api/dashboard/stats").status_code == 401


def test_dashboard_stats_user_ok(user_client: TestClient) -> None:
    r = user_client.get("/api/dashboard/stats")
    assert r.status_code == 200
