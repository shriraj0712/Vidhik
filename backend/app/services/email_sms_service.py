"""
Vidhik Platform - Email & SMS Notification Service
===================================================
Production-grade multi-provider communication service for:
- Cryptographic OTP verification delivery (Email & SMS)
- Real-time security incident alerts (New Device, Location, Password Changed)
- Password reset links & tokens

Supported Providers:
- SMTP (TLS/SSL - Gmail, AWS SES, SendGrid SMTP, Postmark)
- Resend REST API (https://api.resend.com/emails)
- SendGrid REST API (https://api.sendgrid.com/v3/mail/send)
- Twilio SMS Gateway
- MSG91 SMS Gateway
- Development Secure Log fallback (safe masking, never exposes OTP in production)
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
import httpx

logger = logging.getLogger("vidhik.notifications")


class EmailSmsService:
    """Multi-channel secure delivery service."""

    @staticmethod
    def _is_production() -> bool:
        return os.getenv("APP_ENV", "development").lower() == "production"

    @staticmethod
    def _mask_email(email: str) -> str:
        if "@" not in email:
            return "***"
        parts = email.split("@")
        name = parts[0]
        domain = parts[1]
        masked_name = name[:2] + "***" if len(name) > 2 else name[:1] + "***"
        return f"{masked_name}@{domain}"

    @staticmethod
    def _mask_phone(phone: str) -> str:
        clean = phone.strip()
        if len(clean) <= 4:
            return "****"
        return clean[:3] + "****" + clean[-4:]

    # =========================================================================
    # EMAIL DISPATCH
    # =========================================================================

    @staticmethod
    def send_otp_email(
        to_email: str,
        otp_code: str,
        purpose: str = "signup_verification",
        user_name: Optional[str] = None
    ) -> bool:
        """
        Dispatches a secure 6-digit OTP verification code via email.
        """
        recipient_name = user_name or "Vidhik User"
        purpose_titles = {
            "signup_verification": "Verify Your Vidhik Account",
            "registration": "Verify Your Vidhik Account",
            "signup": "Verify Your Vidhik Account",
            "password_reset": "Password Reset Verification Code",
            "email_verification": "Email Verification Code",
            "phone_verification": "Security Verification Code",
            "suspicious_login": "Security Authorization Code"
        }
        title = purpose_titles.get(purpose, "Security Verification Code")
        subject = f"[Vidhik Security] {title}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b1120; color: #e2e8f0; margin: 0; padding: 24px; }}
            .card {{ background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; max-width: 540px; margin: 0 auto; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
            .brand {{ color: #00e5ff; font-size: 24px; font-weight: bold; letter-spacing: 1px; margin-bottom: 8px; }}
            .brand span {{ color: #d4af37; }}
            .title {{ font-size: 20px; font-weight: 600; color: #ffffff; margin-top: 16px; margin-bottom: 8px; }}
            .otp-box {{ background: linear-gradient(135deg, rgba(0, 229, 255, 0.1), rgba(212, 175, 55, 0.1)); border: 1px solid #00e5ff; border-radius: 8px; padding: 18px; text-align: center; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #00e5ff; margin: 24px 0; }}
            .warning {{ background-color: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 12px; font-size: 13px; color: #fca5a5; margin-top: 20px; }}
            .footer {{ font-size: 12px; color: #94a3b8; text-align: center; margin-top: 32px; border-top: 1px solid #334155; padding-top: 16px; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="brand">VIDHIK<span>.AI</span></div>
            <div class="title">{title}</div>
            <p>Hello <strong>{recipient_name}</strong>,</p>
            <p>Use the following verification code to complete your authentication request on the Vidhik AI Legal Platform.</p>
            
            <div class="otp-box">{otp_code}</div>
            
            <p style="font-size: 14px; color: #94a3b8;">This code is valid for <strong>10 minutes</strong>. Never share this code with anyone.</p>
            
            <div class="warning">
              <strong>Security Notice:</strong> If you did not request this code, please ignore this message or change your password immediately.
            </div>
            
            <div class="footer">
              &copy; {datetime.now().year} Vidhik AI Legal Intelligence Platform. All rights reserved.
            </div>
          </div>
        </body>
        </html>
        """

        text_content = f"""
Vidhik AI Legal Platform - {title}
Hello {recipient_name},

Your verification code is: {otp_code}

This code will expire in 10 minutes.
If you did not request this verification, please secure your account immediately.
        """

        return EmailSmsService._dispatch_email(to_email, subject, html_content, text_content)

    @staticmethod
    def send_security_alert_email(
        to_email: str,
        user_name: str,
        alert_type: str,
        title: str,
        description: str,
        device: str,
        location: str,
        ip_address: str
    ) -> bool:
        """
        Sends an urgent security alert when suspicious or new login activity is detected.
        """
        now_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")
        subject = f"[SECURITY ALERT] {title} - Vidhik Account"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0b1120; color: #e2e8f0; margin: 0; padding: 24px; }}
            .card {{ background-color: #1e293b; border-radius: 12px; border: 1px solid #ef4444; max-width: 540px; margin: 0 auto; padding: 32px; box-shadow: 0 10px 25px rgba(239, 68, 68, 0.2); }}
            .brand {{ color: #00e5ff; font-size: 24px; font-weight: bold; margin-bottom: 8px; }}
            .alert-header {{ color: #ef4444; font-size: 18px; font-weight: 700; margin-top: 16px; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }}
            .details-box {{ background-color: #0f172a; border-radius: 8px; border: 1px solid #334155; padding: 16px; margin: 20px 0; font-size: 14px; line-height: 1.6; }}
            .footer {{ font-size: 12px; color: #94a3b8; text-align: center; margin-top: 32px; border-top: 1px solid #334155; padding-top: 16px; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="brand">VIDHIK<span style="color:#d4af37;">.AI</span></div>
            <div class="alert-header">&#9888; Security Alert: {title}</div>
            <p>Hello <strong>{user_name}</strong>,</p>
            <p>{description}</p>
            
            <div class="details-box">
              <strong>Device / Client:</strong> {device}<br>
              <strong>Approximate Location:</strong> {location}<br>
              <strong>IP Address:</strong> {ip_address}<br>
              <strong>Timestamp:</strong> {now_str}
            </div>
            
            <p style="color: #fca5a5;">If this was you, you can safely disregard this email. If you do not recognize this activity, secure your account immediately by signing out all sessions and resetting your password.</p>
            
            <div class="footer">
              &copy; {datetime.now().year} Vidhik AI Legal Intelligence Platform. All rights reserved.
            </div>
          </div>
        </body>
        </html>
        """

        text_content = f"""
[SECURITY ALERT] {title}
Hello {user_name},
{description}

Device: {device}
Location: {location}
IP Address: {ip_address}
Time: {now_str}

If this was NOT you, please log in immediately to sign out unauthorized sessions and reset your password.
        """

        return EmailSmsService._dispatch_email(to_email, subject, html_content, text_content)

    @staticmethod
    def _dispatch_email(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send via the explicitly configured provider; never fake successful delivery."""
        provider = os.getenv("EMAIL_PROVIDER", "smtp").strip().lower()
        from_email = os.getenv("SMTP_FROM_EMAIL", "no-reply@vidhik.ai").strip()
        from_name = os.getenv("SMTP_FROM_NAME", "Vidhik Legal Security").strip()

        if provider == "log":
            logger.warning("Email NOT delivered (log provider) to %s; subject=%r",
                           EmailSmsService._mask_email(to_email), subject)
            return False

        if provider == "smtp":
            host = os.getenv("SMTP_HOST", "").strip()
            user = os.getenv("SMTP_USER", "").strip()
            password = os.getenv("SMTP_PASSWORD", "")
            if not host or not user or not password:
                logger.error("SMTP selected but SMTP_HOST/SMTP_USER/SMTP_PASSWORD is missing.")
                return False
            try:
                port = int(os.getenv("SMTP_PORT", "587"))
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{from_name} <{from_email}>"
                msg["To"] = to_email
                msg.attach(MIMEText(text_body, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))
                with smtplib.SMTP(host, port, timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(user, password)
                    server.sendmail(from_email, [to_email], msg.as_string())
                logger.info("SMTP accepted email for %s", EmailSmsService._mask_email(to_email))
                return True
            except Exception as exc:
                logger.error("SMTP delivery failed for %s (%s)",
                             EmailSmsService._mask_email(to_email), type(exc).__name__)
                return False

        if provider == "resend":
            api_key = os.getenv("RESEND_API_KEY", os.getenv("EMAIL_PROVIDER_API_KEY", "")).strip()
            if not api_key:
                logger.error("Resend selected but API key is missing.")
                return False
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post("https://api.resend.com/emails",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={"from": f"{from_name} <{from_email}>", "to": [to_email],
                              "subject": subject, "html": html_body, "text": text_body})
                if resp.status_code in (200, 201):
                    logger.info("Resend accepted email for %s", EmailSmsService._mask_email(to_email))
                    return True
                logger.error("Resend API returned HTTP %s", resp.status_code)
                return False
            except Exception as exc:
                logger.error("Resend delivery failed (%s)", type(exc).__name__)
                return False

        if provider == "sendgrid":
            api_key = os.getenv("SENDGRID_API_KEY", os.getenv("EMAIL_PROVIDER_API_KEY", "")).strip()
            if not api_key:
                logger.error("SendGrid selected but API key is missing.")
                return False
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post("https://api.sendgrid.com/v3/mail/send",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"personalizations": [{"to": [{"email": to_email}]}],
                              "from": {"email": from_email, "name": from_name},
                              "subject": subject,
                              "content": [{"type": "text/plain", "value": text_body},
                                          {"type": "text/html", "value": html_body}]})
                if resp.status_code in (200, 202):
                    logger.info("SendGrid accepted email for %s", EmailSmsService._mask_email(to_email))
                    return True
                logger.error("SendGrid API returned HTTP %s", resp.status_code)
                return False
            except Exception as exc:
                logger.error("SendGrid delivery failed (%s)", type(exc).__name__)
                return False

        logger.error("Unsupported EMAIL_PROVIDER=%r; no email sent.", provider)
        return False

    # =========================================================================
    # SMS DISPATCH
    # =========================================================================

    @staticmethod
    def send_otp_sms(to_phone: str, otp_code: str, purpose: str = "verification") -> bool:
        """
        Dispatches SMS OTP via Twilio or MSG91 gateway.
        """
        sms_provider = os.getenv("SMS_PROVIDER", "log").lower()
        message_body = f"Your Vidhik AI verification code is {otp_code}. Valid for 10 minutes. Do not share with anyone."

        # 1. Twilio Provider
        if sms_provider == "twilio":
            account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
            from_phone = os.getenv("TWILIO_PHONE_NUMBER", "")

            if account_sid and auth_token and from_phone:
                try:
                    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
                    with httpx.Client(timeout=6.0) as client:
                        resp = client.post(
                            url,
                            data={
                                "From": from_phone,
                                "To": to_phone,
                                "Body": message_body
                            },
                            auth=(account_sid, auth_token)
                        )
                        if resp.status_code in (200, 201):
                            logger.info(f"Twilio SMS dispatched to {EmailSmsService._mask_phone(to_phone)}")
                            return True
                        logger.error(f"Twilio API error: {resp.status_code} - {resp.text}")
                except Exception as e:
                    logger.error(f"Twilio SMS dispatch failed: {e}")
                if EmailSmsService._is_production():
                    return False
            elif EmailSmsService._is_production():
                logger.error("Twilio SMS credentials missing in production configuration.")
                return False

        # 2. MSG91 Provider
        elif sms_provider == "msg91":
            auth_key = os.getenv("MSG91_AUTH_KEY", os.getenv("SMS_PROVIDER_API_KEY", ""))
            sender_id = os.getenv("MSG91_SENDER_ID", os.getenv("SMS_PROVIDER_SENDER_ID", "VIDHIK"))
            template_id = os.getenv("MSG91_TEMPLATE_ID", "")

            if auth_key:
                try:
                    with httpx.Client(timeout=6.0) as client:
                        resp = client.post(
                            "https://api.msg91.com/api/v5/otp",
                            headers={"authkey": auth_key, "Content-Type": "application/json"},
                            json={
                                "template_id": template_id,
                                "mobile": to_phone.replace("+", ""),
                                "otp": otp_code
                            }
                        )
                        if resp.status_code == 200:
                            logger.info(f"MSG91 SMS dispatched to {EmailSmsService._mask_phone(to_phone)}")
                            return True
                        logger.error(f"MSG91 API error: {resp.status_code} - {resp.text}")
                except Exception as e:
                    logger.error(f"MSG91 SMS dispatch failed: {e}")
                if EmailSmsService._is_production():
                    return False
            elif EmailSmsService._is_production():
                logger.error("MSG91 credentials missing in production configuration.")
                return False

        # Log/mock/none are not delivery channels.
        if sms_provider in ("log", "mock", "none"):
            logger.warning("SMS NOT delivered (provider=%s) to %s",
                           sms_provider, EmailSmsService._mask_phone(to_phone))
            return False

        logger.error("Unsupported or incompletely configured SMS provider=%r; SMS not sent.", sms_provider)
        return False

