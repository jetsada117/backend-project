import pytest
from httpx import AsyncClient
import json

@pytest.fixture
async def auth_headers(client: AsyncClient):
    # Setup: Register and login a user
    files = {"file": ("test.jpg", b"fake-image", "image/jpeg")}
    await client.post("/api/v1/auth/register", data={
        "first_name": "Search", "last_name": "User", 
        "email": "search@example.com", "password": "pass", "otp_code": "1234"
    }, files=files)
    
    login_res = await client.post("/api/v1/auth/login", json={"email": "search@example.com", "password": "pass"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_search_similarity(client: AsyncClient, auth_headers: dict):
    # 1. Save a prediction first to search against
    predictions_dict = {
        "age_result": [0, 0, 1, 0, 0, 0], # วัยรุ่น
        "gender_result": [0, 1],         # ชาย
        "haircolor_result": [0, 0, 1],   # ผมดำ
        "hairstyle_result": [1, 0],      # ผมตรง
        "eyebrows_result": [1, 0, 0, 0], # คิ้วโก่ง
        "skin_result": [1, 0, 0, 0],      # ผิวขาว
        "beard_result": [0, 0, 0, 0]      # ไม่ระบุ
    }
    
    files = {"file": ("face.jpg", b"fake-face-content", "image/jpeg")}
    data = {"predictions_json": json.dumps(predictions_dict)}
    await client.post("/api/v1/predictions/save", headers=auth_headers, data=data, files=files)
    
    # 2. Search with similar description
    params = {"description": "ผู้ชาย วัยรุ่น ผมตรง", "limit": 4}
    response = await client.get("/api/v1/search", headers=auth_headers, params=params)
    
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0
    assert results[0]["similarity_score"] > 50 # Should be high match
