import asyncio
import logging
import smtplib
from email.message import EmailMessage
from app.core.config import settings

log = logging.getLogger("mezflow.notify")


class NotifyError(RuntimeError):
    pass


def _send_smtp(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
        smtp.send_message(msg)


async def send_email(to: str, subject: str, body: str) -> None:
    """
    Sends through SMTP when SMTP_HOST is set (e.g. Gmail App Password).
    Without it, dev prints to the API console; production refuses, because the body carries a secret.
    """
    if settings.SMTP_HOST:
        try:
            await asyncio.to_thread(_send_smtp, to, subject, body)
        except Exception as exc:
            log.error("SMTP send to %s failed: %s", to, exc)
            raise NotifyError("Could not send e-mail") from exc
        return
    if settings.ENVIRONMENT == "production":
        log.error("SMTP_HOST is not set; e-mail to %s not sent", to)
        raise NotifyError("E-mail is not configured")
    print(f"[NOTIFY] to={to} | {subject}\n{body}", flush=True)
