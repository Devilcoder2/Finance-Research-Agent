import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.api.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)
from backend.app.api.research import close_pool

def test_password_hashing():
    password = "MySecurePassword123"
    hashed = hash_password(password)
    
    assert hashed.startswith("scrypt:16384:8:1$")
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_jwt_tokens():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    
    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded == user_id
    
    # Invalid token check
    assert decode_access_token("invalid_token_string") is None

@pytest.mark.asyncio
async def test_auth_signup_and_login_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        unique_email = f"analyst_{uuid.uuid4()}@example.com"
        password = "test_password"
        
        # 1. Test signup with invalid email format
        invalid_signup = await ac.post(
            "/api/auth/signup",
            json={"email": "invalid_email", "password": password}
        )
        assert invalid_signup.status_code == 400
        
        # 2. Test successful signup
        signup_res = await ac.post(
            "/api/auth/signup",
            json={"email": unique_email, "password": password}
        )
        assert signup_res.status_code == 201
        signup_data = signup_res.json()
        assert signup_data["email"] == unique_email
        assert "id" in signup_data
        
        # 3. Test signup with duplicate email
        duplicate_signup = await ac.post(
            "/api/auth/signup",
            json={"email": unique_email, "password": password}
        )
        assert duplicate_signup.status_code == 400
        
        # 4. Test login with wrong password
        login_fail = await ac.post(
            "/api/auth/login",
            json={"email": unique_email, "password": "wrong_password"}
        )
        assert login_fail.status_code == 401
        
        # 5. Test successful login
        login_res = await ac.post(
            "/api/auth/login",
            json={"email": unique_email, "password": password}
        )
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert "access_token" in login_data
        assert login_data["token_type"] == "bearer"
        
        # 6. Test securing a route (unauthenticated request)
        threads_fail = await ac.get("/api/research/threads")
        assert threads_fail.status_code == 401
        
        # 7. Test securing a route (authenticated request)
        token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        threads_success = await ac.get("/api/research/threads", headers=headers)
        assert threads_success.status_code == 200
        assert isinstance(threads_success.json(), list)

    await close_pool()
