import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def save_otp(email: str, otp_code: str, expire_minutes: int = 5):
    """
    บันทึก OTP ลงใน Redis พร้อมตั้งเวลาลบอัตโนมัติ (TTL)
    """
    await redis_client.setex(f"otp:{email}", expire_minutes * 60, otp_code)


async def verify_otp(email: str, input_otp: str) -> bool:
    """
    ตรวจสอบ OTP และลบทิ้งทันทีถ้าถูกต้องเพื่อป้องกันการใช้ซ้ำ
    """
    stored_otp = await redis_client.get(f"otp:{email}")
    if stored_otp and stored_otp == input_otp:
        await redis_client.delete(f"otp:{email}")
        return True
    return False
