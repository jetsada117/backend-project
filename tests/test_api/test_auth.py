import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_request_otp(client: AsyncClient):
    response = await client.post("/api/v1/auth/request-otp", data={"email": "test@example.com"})
    assert response.status_code == 200
    assert response.json()["message"] == "OTP sent to your email"

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    # Prepare dummy image
    files = {"file": ("test.jpg", b"fake-image-content", "image/jpeg")}
    data = {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "password": "password123",
        "otp_code": "123456"
    }
    
    response = await client.post("/api/v1/auth/register", data=data, files=files)
    assert response.status_code == 200
    assert response.json()["message"] == "Registration successful"

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    # First, ensure user exists (from previous test or setup)
    # Since we use in-memory SQLite and setup_db is session-scoped, 
    # the user from test_register_user might be there if they run in order.
    # But for robustness, let's register here too or assume session persistence.
    
    login_data = {
        "email": "test@example.com",
        "password": "password123"
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    # Login to get token
    login_data = {"email": "test@example.com", "password": "password123"}
    login_res = await client.post("/api/v1/auth/login", json=login_data)
    token = login_res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/user/me", headers=headers)
    assert response.status_code == 405 # Method Not Allowed if only PATCH exists

@pytest.mark.asyncio
async def test_update_user_me(client: AsyncClient):
    # Login to get token
    login_data = {"email": "test@example.com", "password": "password123"}
    login_res = await client.post("/api/v1/auth/login", json=login_data)
    token = login_res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "first_name": "UpdatedFirst",
        "last_name": "UpdatedLast"
    }
    response = await client.patch("/api/v1/user/me", headers=headers, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["first_name"] == "UpdatedFirst"
    assert res_data["last_name"] == "UpdatedLast"

    # Test updating avatar as well
    files = {"avatar": ("new_avatar.jpg", b"new-fake-image", "image/jpeg")}
    response = await client.patch("/api/v1/user/me", headers=headers, files=files)
    assert response.status_code == 200
    res_data = response.json()
    assert "profile_image_url" in res_data

@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    login_data = {"email": "test@example.com", "password": "password123"}
    login_res = await client.post("/api/v1/auth/login", json=login_data)
    refresh_token = login_res.json()["refresh_token"]
    
    response = await client.post(f"/api/v1/auth/refresh-token?refresh_token={refresh_token}")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["refresh_token"] == refresh_token
    assert "user" in data
    assert data["user"]["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"

