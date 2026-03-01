import httpx
from app.core.config import settings


async def send_otp_email(email_to: str, otp_code: str):
    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }

    payload = {
        "sender": {"name": "FaceSearch AI", "email": settings.GMAIL},
        "to": [{"email": email_to}],
        "subject": "รหัส OTP สำหรับยืนยันตัวตน FaceSearch AI",
        "htmlContent": f"""
        <html>
            <body>
                <h2>ยินดีต้อนรับสู่ FaceSearch AI</h2>
                <p>รหัสยืนยันตัวตนของคุณคือ: <strong style="font-size: 24px; color: #4F46E5;">{otp_code}</strong></p>
                <p>รหัสนี้มีอายุการใช้งาน 5 นาที</p>
            </body>
        </html>
        """,
    }

    try:
        # ใช้ httpx เพื่อยิง API ออกไปที่พอร์ต 443 (ทะลุบล็อก 100%)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=headers, json=payload, timeout=10.0
            )

            if response.status_code in (201, 200):
                print(f"✅ ส่งอีเมล OTP สำเร็จ (ผ่าน Brevo API)")
            else:
                print(f"❌ เกิดข้อผิดพลาดจาก Brevo: {response.text}")

    except Exception as e:
        print(f"❌ ไม่สามารถส่ง API ได้: {e}")
