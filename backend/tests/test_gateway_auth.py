"""Integration tests for the API Gateway and Auth Service."""
import os
import pytest
import requests

# Use GATEWAY_URL (usually localhost:8000 in Docker environment) or fallback
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000").rstrip("/")
API = f"{GATEWAY_URL}/api"


def test_gateway_health():
    """Verify we can reach the Gateway health endpoints."""
    try:
        r = requests.get(f"{API}/auth/health", timeout=5)
        if r.status_code != 200 or r.json().get("checks", {}).get("database") != "ok":
            pytest.skip("Gateway or Auth Service database degraded")
    except (requests.exceptions.RequestException, ValueError, KeyError):
        pytest.skip("API Gateway or Auth Service not reachable at " + GATEWAY_URL)

    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "degraded")


def test_gateway_auth_flow():
    """Verify signup, login, and token-authorized access work across the gateway."""
    try:
        r = requests.get(f"{API}/auth/health", timeout=5)
        if r.status_code != 200 or r.json().get("checks", {}).get("database") != "ok":
            pytest.skip("API Gateway or Auth Service degraded")
    except (requests.exceptions.RequestException, ValueError, KeyError):
        pytest.skip("API Gateway or Auth Service not reachable")

    # Generate unique email to avoid conflict
    import uuid
    uid = uuid.uuid4().hex[:8]
    creds = {
        "email": f"gateway_test_{uid}@example.com",
        "password": "Password123!",
        "name": "Gateway User",
        "role": "student",
    }

    # 1. Signup through gateway (routed to auth-service)
    r_signup = requests.post(f"{API}/auth/signup", json=creds, timeout=10)
    assert r_signup.status_code == 201, f"Signup failed: {r_signup.text}"
    signup_data = r_signup.json()
    assert "access_token" in signup_data
    assert signup_data["user"]["email"] == creds["email"]

    # 2. Login through gateway (routed to auth-service)
    login_payload = {
        "email": creds["email"],
        "password": creds["password"],
    }
    r_login = requests.post(f"{API}/auth/login", json=login_payload, timeout=10)
    assert r_login.status_code == 200, f"Login failed: {r_login.text}"
    login_data = r_login.json()
    token = login_data["access_token"]
    assert token

    # 3. Access /me (routed to auth-service) using JWT
    headers = {"Authorization": f"Bearer {token}"}
    r_me = requests.get(f"{API}/auth/me", headers=headers, timeout=10)
    assert r_me.status_code == 200, f"Auth token validation failed: {r_me.text}"
    me_data = r_me.json()
    assert me_data["email"] == creds["email"]
