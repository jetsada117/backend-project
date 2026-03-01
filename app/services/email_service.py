import smtplib
import socket
from email.mime.text import MIMEText
from app.core.config import settings


def send_otp_email(email_to: str, otp_code: str):
    msg = MIMEText(f"รหัส OTP ของคุณคือ: {otp_code}")
    msg["Subject"] = "Verification Code - FaceSearch AI"
    msg["From"] = settings.SMTP_USER
    msg["To"] = email_to

    try:
        smtp_server = "smtp.gmail.com"
        ipv4_address = socket.gethostbyname(smtp_server)
        print(f"เชื่อมต่อไปที่ IP: {ipv4_address}")

        # 2. เชื่อมต่อผ่าน IP ตรงๆ แทนการใช้ชื่อ
        with smtplib.SMTP_SSL(ipv4_address, 465) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, email_to, msg.as_string())
            print("✅ ส่งอีเมลสำเร็จ!")

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
