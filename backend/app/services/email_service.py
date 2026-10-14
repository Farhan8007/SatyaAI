"""
Sends real emails via SMTP (works with Gmail if you set up an App Password
-- see README for instructions).

If smtp_username / smtp_password aren't configured, this silently skips
sending and just logs to the console -- so the app keeps working even
without email set up, it just won't actually deliver anything.
"""
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from app.config import settings


def _send(to_email: str, subject: str, body: str) -> bool:
    if not settings.smtp_username or not settings.smtp_password:
        print(f"[email] SMTP not configured -- skipping email to {to_email}. "
              f"(Set smtp_username/smtp_password in backend/.env to enable this.)")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = f"SATYA AI <{settings.smtp_username}>"
    msg["To"] = to_email
    # Gmail (and most spam filters) treat mail missing these standard headers
    # as suspicious and may silently drop it -- not even into Spam, just gone.
    # A plain smtplib.MIMEText doesn't set them by default, so we add them
    # explicitly to look like a normal, legitimate email client.
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=settings.smtp_username.split("@")[-1])
    msg["Reply-To"] = settings.smtp_username

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_username, [to_email], msg.as_string())
        print(f"[email] Sent to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[email] Failed to send to {to_email}: {e}")
        return False


def send_invite_email(to_email: str, name: str, role: str, password: str, verification_token: str) -> bool:
    """
    Sent right after an account is created (self-signup or admin invite).
    Includes the login credentials AND a verification link -- the account
    can't actually be used to log in until that link is clicked, which
    proves the email address is real and belongs to whoever it was meant for.
    """
    role_label = role.replace("_", " ").title()
    verify_link = f"{settings.frontend_url}/verify-email?token={verification_token}"

    subject = "Verify your email for SATYA AI"
    body = (
        f"Hi {name},\n\n"
        f"You've been added to SATYA AI as a {role_label}.\n\n"
        f"Before you can sign in, please verify this email address:\n"
        f"{verify_link}\n\n"
        f"Once verified, log in here: {settings.frontend_url}/login\n"
        f"Email: {to_email}\n"
        f"Password: {password}\n\n"
        f"Please keep this password safe and don't share it.\n\n"
        f"-- SATYA AI"
    )
    return _send(to_email, subject, body)
