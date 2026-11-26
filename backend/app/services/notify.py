import asyncio
import html as html_lib
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Optional
from app.core.config import settings

log = logging.getLogger("mezflow.notify")


class NotifyError(RuntimeError):
    pass


def _send_smtp(to: str, subject: str, body: str, html: Optional[str] = None) -> None:
    msg = EmailMessage()
    sender = settings.SMTP_FROM or settings.SMTP_USER
    # Inbox shows "MezFlow" as the sender name instead of the bare Gmail address
    msg["From"] = sender if "<" in sender else formataddr((settings.SMTP_FROM_NAME, sender))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1].strip(">"))
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
        smtp.send_message(msg)


async def send_email(to: str, subject: str, body: str, html: Optional[str] = None) -> None:
    """
    Sends through SMTP when SMTP_HOST is set (e.g. Gmail App Password).
    Without it, dev prints to the API console; production refuses, because the body carries a secret.
    """
    if settings.SMTP_HOST:
        try:
            await asyncio.to_thread(_send_smtp, to, subject, body, html)
        except Exception as exc:
            log.error("SMTP send to %s failed: %s", to, exc)
            raise NotifyError("Could not send e-mail") from exc
        return
    if settings.ENVIRONMENT == "production":
        log.error("SMTP_HOST is not set; e-mail to %s not sent", to)
        raise NotifyError("E-mail is not configured")
    print(f"[NOTIFY] to={to} | {subject}\n{body}", flush=True)


def _code_html(heading: str, intro: str, code: str, minutes: int, footer: str) -> str:
    """Table layout with inline styles: the only thing every mail client (Gmail, Outlook, phones) renders reliably."""
    e = html_lib.escape
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f4f4f5;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:32px 12px;">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border-radius:16px;font-family:Arial,Helvetica,sans-serif;color:#18181b;">
<tr><td style="padding:28px 32px 0;">
<span style="display:inline-block;background:#f97316;color:#ffffff;font-weight:bold;font-size:16px;border-radius:8px;padding:6px 11px;">M</span>
<span style="font-size:18px;font-weight:bold;vertical-align:middle;padding-left:8px;">MezFlow</span>
</td></tr>
<tr><td style="padding:24px 32px 0;">
<h1 style="margin:0 0 12px;font-size:20px;">{e(heading)}</h1>
<p style="margin:0;font-size:15px;line-height:22px;color:#3f3f46;">{e(intro)}</p>
</td></tr>
<tr><td align="center" style="padding:24px 32px;">
<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;padding:18px 0;font-size:34px;font-weight:bold;letter-spacing:10px;color:#c2410c;font-family:'Courier New',monospace;">{e(code)}</div>
<p style="margin:12px 0 0;font-size:13px;color:#71717a;">This code expires in {minutes} minutes. Never share it with anyone.</p>
</td></tr>
<tr><td style="padding:0 32px 28px;">
<p style="margin:0;font-size:13px;line-height:20px;color:#71717a;">{e(footer)}</p>
</td></tr>
</table>
<p style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#a1a1aa;margin:16px 0 0;">MezFlow &middot; Restaurant operations, live from table to kitchen</p>
</td></tr></table>
</body></html>"""


async def send_code_email(to: str, *, purpose: str, code: str, minutes: int) -> None:
    """One look for every code e-mail; the code is also in the subject so it shows in the inbox preview."""
    copy = {
        "signup": (
            "Verify your email",
            "Welcome to MezFlow! Enter this code to finish creating your restaurant workspace.",
            "If you did not try to create a MezFlow account, you can safely ignore this email.",
        ),
        "reset": (
            "Reset your password",
            "We received a request to reset your MezFlow password. Enter this code to choose a new one.",
            "If you did not ask to reset your password, ignore this email. Your password stays the same.",
        ),
    }
    heading, intro, footer = copy[purpose]
    subject = f"{code} is your MezFlow {'verification' if purpose == 'signup' else 'password reset'} code"
    text = f"{heading}\n\n{intro}\n\nYour code: {code}\n\nThis code expires in {minutes} minutes. Never share it with anyone.\n\n{footer}\n\n- MezFlow"
    await send_email(to, subject, text, html=_code_html(heading, intro, code, minutes, footer))
