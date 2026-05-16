"""
SMTP email service for sending OTP codes and notifications.
Uses configurable SMTP settings from .env — nothing hardcoded.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """
    Send an email via SMTP.
    Returns True on success, False on failure.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to

        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to, msg.as_string())

        logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email send failed to {to}: {e}")
        return False


def send_otp_email(to: str, otp_code: str, user_name: str = "User") -> bool:
    """
    Send a beautiful HTML OTP verification email.
    """
    subject = f"{settings.PROJECT_NAME} — Your Verification Code"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f4f7fa; margin: 0; padding: 20px; }}
            .container {{ max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px; text-align: center; color: #fff; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .body {{ padding: 32px; text-align: center; }}
            .otp-code {{ font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #667eea; background: #f0f0ff; padding: 16px 32px; border-radius: 8px; display: inline-block; margin: 20px 0; }}
            .note {{ color: #888; font-size: 13px; margin-top: 20px; }}
            .footer {{ text-align: center; padding: 16px; background: #f9f9f9; color: #aaa; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{settings.PROJECT_NAME}</h1>
            </div>
            <div class="body">
                <p>Hello <strong>{user_name}</strong>,</p>
                <p>Your verification code is:</p>
                <div class="otp-code">{otp_code}</div>
                <p class="note">This code will expire in 15 minutes.<br>If you didn't request this, please ignore this email.</p>
            </div>
            <div class="footer">
                &copy; 2024 {settings.PROJECT_NAME}. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(to, subject, html_body)


def send_notification_email(to: str, title: str, message: str, user_name: str = "User") -> bool:
    """
    Send a notification email (borrow approved, book returned, etc.).
    """
    subject = f" {settings.PROJECT_NAME} — {title}"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f4f7fa; margin: 0; padding: 20px; }}
            .container {{ max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 24px; text-align: center; color: #fff; }}
            .header h1 {{ margin: 0; font-size: 20px; }}
            .body {{ padding: 24px; }}
            .body h2 {{ color: #333; margin-top: 0; }}
            .body p {{ color: #555; line-height: 1.6; }}
            .footer {{ text-align: center; padding: 16px; background: #f9f9f9; color: #aaa; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1> {settings.PROJECT_NAME}</h1>
            </div>
            <div class="body">
                <h2>{title}</h2>
                <p>Hello <strong>{user_name}</strong>,</p>
                <p>{message}</p>
            </div>
            <div class="footer">
                &copy; 2024 {settings.PROJECT_NAME}. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(to, subject, html_body)
