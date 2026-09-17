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


def test_oauth2_form_login_and_openapi():
    # 1. Test OAuth2 form-urlencoded login (Swagger UI style)
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin@smartmom.test", "password": "Admin@12345"},
    )
    assert login_resp.status_code == 200, f"Form login failed: {login_resp.text}"
    data = login_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "token" in data

    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test protected endpoint with OAuth2 form login token
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "admin@smartmom.test"

    # 3. Check OpenAPI schema for OAuth2PasswordBearer
    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    schema = openapi_resp.json()
    assert "components" in schema
    assert "securitySchemes" in schema["components"]
    sec_schemes = schema["components"]["securitySchemes"]
    assert "OAuth2PasswordBearer" in sec_schemes
    assert sec_schemes["OAuth2PasswordBearer"]["type"] == "oauth2"
    assert (
        sec_schemes["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"]
        == "/api/auth/login"
    )
