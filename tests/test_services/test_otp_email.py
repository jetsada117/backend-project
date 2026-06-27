import os
import random
import httpx
import pytest
import redis.asyncio as redis
from pathlib import Path
from httpx import AsyncClient

from app.core.config import settings
from app.services import redis_service, email_service

# =====================================================================
# Helper to read real .env file and bypass pytest.ini dummy overrides
# =====================================================================
def get_real_env():
    env_vars = {}
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()
    return env_vars


# =====================================================================
# Override global autouse mocks from conftest.py
# This allows us to test the actual services with mock/real objects
# =====================================================================
@pytest.fixture(autouse=True)
def mock_external_services():
    """
    Override the global mock fixture to NOT mock redis_service and email_service.
    We will manage mocks inside each test case individually.
    """
    pass


# =====================================================================
# 1. UNIT TESTS WITH MOCKS (Always run during normal test execution)
# =====================================================================

@pytest.mark.asyncio
async def test_redis_save_otp_mocked(mocker):
    """ทดสอบบันทึก OTP ลง Redis (Mock)"""
    mock_redis = mocker.patch("app.services.redis_service.redis_client")
    mock_redis.setex = mocker.AsyncMock()
    
    email = "unit-test@example.com"
    otp = "1234"
    await redis_service.save_otp(email, otp, expire_minutes=5)
    
    # ตรวจสอบการเรียก setex ด้วย key, TTL (5 นาที = 300 วินาที), และ otp
    mock_redis.setex.assert_called_once_with(f"otp:{email}", 300, otp)


@pytest.mark.asyncio
async def test_redis_verify_otp_success_mocked(mocker):
    """ทดสอบยืนยัน OTP สำเร็จ (Mock)"""
    mock_redis = mocker.patch("app.services.redis_service.redis_client")
    mock_redis.get = mocker.AsyncMock(return_value="1234")
    mock_redis.delete = mocker.AsyncMock()
    
    email = "unit-test@example.com"
    is_valid = await redis_service.verify_otp(email, "1234")
    
    assert is_valid is True
    mock_redis.get.assert_called_once_with(f"otp:{email}")
    mock_redis.delete.assert_called_once_with(f"otp:{email}")


@pytest.mark.asyncio
async def test_redis_verify_otp_failure_mocked(mocker):
    """ทดสอบยืนยัน OTP ไม่สำเร็จ หรือใส่ผิด (Mock)"""
    mock_redis = mocker.patch("app.services.redis_service.redis_client")
    mock_redis.get = mocker.AsyncMock(return_value="1234")
    mock_redis.delete = mocker.AsyncMock()
    
    email = "unit-test@example.com"
    is_valid = await redis_service.verify_otp(email, "9999")  # OTP ไม่ตรง
    
    assert is_valid is False
    mock_redis.get.assert_called_once_with(f"otp:{email}")
    mock_redis.delete.assert_not_called()  # ต้องไม่ลบหากยืนยันไม่ผ่าน


@pytest.mark.asyncio
async def test_send_otp_email_mocked(mocker):
    """ทดสอบการเรียกส่งอีเมลผ่าน Brevo API (Mock)"""
    # Mock httpx.AsyncClient
    mock_client = mocker.AsyncMock()
    mock_response = mocker.Mock()
    mock_response.status_code = 201
    mock_response.text = '{"messageId": "<mock-id>"}'
    mock_client.post.return_value = mock_response
    
    # Mock context manager สำหรับ httpx.AsyncClient()
    mock_client_class = mocker.patch("httpx.AsyncClient")
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    email = "unit-test@example.com"
    otp = "5678"
    
    await email_service.send_otp_email(email, otp)
    
    # ตรวจสอบว่ามีการเรียก API ถูกต้อง
    mock_client_class.assert_called_once()
    mock_client.post.assert_called_once()
    
    args, kwargs = mock_client.post.call_args
    assert args[0] == "https://api.brevo.com/v3/smtp/email"
    assert kwargs["headers"]["api-key"] == "test-brevo-key"
    assert kwargs["json"]["to"] == [{"email": email}]
    assert otp in kwargs["json"]["htmlContent"]


@pytest.mark.asyncio
async def test_request_otp_endpoint_mocked(client: AsyncClient, mocker):
    """ทดสอบ Endpoint /request-otp ด้วย Mock"""
    # Mock การทำงานของ Service เพื่อไม่ให้เชื่อมต่อของจริงระหว่างรันเทสปกติ
    mock_save_otp = mocker.patch("app.api.v1.endpoints.auth.redis_service.save_otp", return_value=None)
    mock_send_email = mocker.patch("app.api.v1.endpoints.auth.email_service.send_otp_email", return_value=None)
    
    response = await client.post("/api/v1/auth/request-otp", data={"email": "newuser@example.com"})
    
    assert response.status_code == 200
    assert response.json()["message"] == "OTP sent to your email"
    
    mock_save_otp.assert_called_once()
    mock_send_email.assert_called_once()


# =====================================================================
# 2. INTEGRATION TESTS (เชื่อมต่อจริงกับ Redis Cloud และ Brevo)
# จะทำงานเมื่อพบ credentials จริงในไฟล์ .env เท่านั้น (มิฉะนั้นจะ Skip อัตโนมัติ)
# =====================================================================

@pytest.mark.asyncio
async def test_redis_otp_real(mocker):
    """ทดสอบใช้งาน Redis จริงจาก .env เพื่อบันทึกและตรวจสอบ OTP"""
    real_env = get_real_env()
    redis_url = real_env.get("REDIS_URL")
    
    # หากไม่มี Redis Cloud URL ให้ข้ามเทสนี้
    if not redis_url or "localhost" in redis_url:
        pytest.skip("ข้ามการทดสอบ Redis จริงเนื่องจากไม่พบ REDIS_URL ของจริงใน .env")
        
    # เปลี่ยนมาใช้ redis_client จริงสำหรับเคสนี้
    real_redis_client = redis.from_url(redis_url, decode_responses=True)
    mocker.patch("app.services.redis_service.redis_client", real_redis_client)
    
    test_email = "real-test-otp@example.com"
    test_otp = f"{random.randint(1000, 9999)}"
    
    try:
        # 1. เคลียร์ค่าเก่าก่อนเริ่ม
        await real_redis_client.delete(f"otp:{test_email}")
        
        # 2. บันทึก OTP
        await redis_service.save_otp(test_email, test_otp, expire_minutes=1)
        
        # 3. ลองตรวจรหัสที่ผิด
        is_valid_wrong = await redis_service.verify_otp(test_email, "0000")
        assert is_valid_wrong is False
        
        # 4. ตรวจรหัสที่ถูกต้อง
        is_valid_correct = await redis_service.verify_otp(test_email, test_otp)
        assert is_valid_correct is True
        
        # 5. ตรวจซ้ำอีกครั้ง (ต้องเป็น False เพราะ OTP ควรลบทิ้งหลังใช้งานสำเร็จ)
        is_valid_again = await redis_service.verify_otp(test_email, test_otp)
        assert is_valid_again is False
        
    finally:
        await real_redis_client.aclose()


@pytest.mark.asyncio
async def test_send_otp_email_real(mocker):
    """ส่งอีเมล OTP จริงเข้าเมลล์ตัวเอง (ใช้ Brevo API Key จริงใน .env)"""
    real_env = get_real_env()
    brevo_key = real_env.get("BREVO_API_KEY")
    gmail_sender = real_env.get("GMAIL")
    
    # หากไม่มี Brevo API Key ของจริง ให้ข้ามเทสนี้
    if not brevo_key or brevo_key.startswith("test-"):
        pytest.skip("ข้ามการส่งอีเมลจริงเนื่องจากไม่พบ BREVO_API_KEY ของจริงใน .env")
        
    # แพตช์ค่า config ใน email_service ด้วย credentials จริง
    mocker.patch("app.services.email_service.settings.BREVO_API_KEY", brevo_key)
    mocker.patch("app.services.email_service.settings.GMAIL", gmail_sender)
    
    # ส่งเข้าอีเมลผู้รับ (หากกำหนด TEST_RECIPIENT_EMAIL ใน .env จะส่งไปที่นั่น มิฉะนั้นจะส่งเข้าอีเมลตัวเองที่ส่ง)
    target_email = real_env.get("TEST_RECIPIENT_EMAIL") or gmail_sender
    
    test_otp = f"{random.randint(1000, 9999)}"
    print(f"\n[INFO] กำลังส่งอีเมลจริงไปที่ {target_email} ด้วย OTP: {test_otp}...")
    
    # ตรงนี้จะทำการส่งอีเมลจริงออกไป
    # ถ้าทำงานสำเร็จ จะไม่เกิด Exception และ print SUCCESS
    await email_service.send_otp_email(target_email, test_otp)
