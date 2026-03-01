import smtplib
from email.mime.text import MIMEText
from app.core.config import settings


def send_otp_email(email_to: str, otp_code: str):
    msg = MIMEText(f"Your FaceSearch AI OTP is: {otp_code}")
    msg["Subject"] = "Verification Code"
    msg["From"] = settings.SMTP_USER
    msg["To"] = email_to

    try:
        # เปลี่ยนจากการใช้ SMTP(587) มาเป็น SMTP_SSL(465)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, email_to, msg.as_string())
    except Exception as e:
        print(f"Failed to send email: {e}")
