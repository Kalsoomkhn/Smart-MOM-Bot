from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_auth_and_protected_endpoints_flow():
    # 1. Login with demo organizer
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "admin@smartmom.test", "password": "Admin@12345"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    data = login_resp.json()
    assert "token" in data
    assert "user" in data
    token = data["token"]
    assert token

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Access /api/auth/me with token
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200, f"/api/auth/me failed: {me_resp.text}"
    user_info = me_resp.json()
    assert user_info["email"] == "admin@smartmom.test"

    # 3. Access /api/meetings with token
    meetings_resp = client.get("/api/meetings", headers=headers)
    assert (
        meetings_resp.status_code == 200
    ), f"/api/meetings failed: {meetings_resp.text}"
    meetings = meetings_resp.json()
    assert isinstance(meetings, list)

    # 4. Access without token should be 401
    no_auth_resp = client.get("/api/meetings")
    assert no_auth_resp.status_code == 401
    assert no_auth_resp.json() == {"error": "Authentication required."}

    # 5. Access with invalid token should be 401
    bad_auth_resp = client.get(
        "/api/meetings", headers={"Authorization": "Bearer invalid.jwt.token"}
    )
    assert bad_auth_resp.status_code == 401
    assert bad_auth_resp.json() == {"error": "Authentication required."}
