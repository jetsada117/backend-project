import pytest
import json
from httpx import AsyncClient

@pytest.fixture
async def auth_headers(client: AsyncClient):
    # Setup: Register and login a user
    files = {"file": ("test.jpg", b"fake-image", "image/jpeg")}
    await client.post("/api/v1/auth/register", data={
        "first_name": "Pred", "last_name": "User", 
        "email": "pred@example.com", "password": "pass", "otp_code": "1234"
    }, files=files)
    
    login_res = await client.post("/api/v1/auth/login", json={"email": "pred@example.com", "password": "pass"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_predict_image(client: AsyncClient, auth_headers: dict):
    files = {"file": ("face.jpg", b"fake-face-content", "image/jpeg")}
    response = await client.post("/api/v1/predictions/", headers=auth_headers, files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert "features" in data
    assert "descriptions" in data

@pytest.mark.asyncio
async def test_save_prediction(client: AsyncClient, auth_headers: dict):
    # Mock prediction data
    predictions_dict = {
        "age_result": [0, 0, 1, 0, 0, 0],
        "gender_result": [0, 1],
        "haircolor_result": [0, 0, 1],
        "hairstyle_result": [1, 0],
        "eyebrows_result": [1, 0, 0, 0],
        "skin_result": [1, 0, 0, 0],
        "beard_result": [0, 0, 0, 0]
    }
    
    files = {"file": ("face.jpg", b"fake-face-content", "image/jpeg")}
    data = {"predictions_json": json.dumps(predictions_dict)}
    
    response = await client.post("/api/v1/predictions/save", headers=auth_headers, data=data, files=files)
    
    assert response.status_code == 200
    res_data = response.json()
    assert "prediction_id" in res_data
    assert res_data["gender_result"] == "ชาย"
