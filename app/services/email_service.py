import smtplib
from email.mime.text import MIMEText
from app.core.config import settings


def send_otp_email(email_to: str, otp_code: str):
    msg = MIMEText(f"Your FaceSearch AI OTP is: {otp_code}")
    msg["Subject"] = "Verification Code"
    msg["From"] = settings.SMTP_USER
    msg["To"] = email_to

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USER, email_to, msg.as_string())
