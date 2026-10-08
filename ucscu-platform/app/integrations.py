"""On-premises integrations: Kyocera LAN printing and optional email.

Both are optional. If they are not configured (or unreachable) the caller gets a
clear error instead of a crash, so the app still works on a bare LAN.
"""
import smtplib
import socket
from email.message import EmailMessage

from .models import get_setting

PRINT_TIMEOUT = 6


def printer_configured():
    return bool((get_setting("printer_host") or "").strip())


def print_raw(text, title=""):
    """Send plain text to a network printer's raw port (Kyocera default 9100).

    Returns (ok, message).
    """
    host = (get_setting("printer_host") or "").strip()
    if not host:
        return False, "No printer configured. Set the printer IP on the LAN Setup screen."
    try:
        port = int((get_setting("printer_port") or "9100").strip() or 9100)
    except ValueError:
        port = 9100
    if title:
        text = "%s\n%s\n\n%s" % (title, "=" * len(title), text)
    payload = b"\x1b@" + text.encode("utf-8", "replace") + b"\n\n\n\x1b\x45\x0c"
    try:
        with socket.create_connection((host, port), timeout=PRINT_TIMEOUT) as sock:
            sock.sendall(payload)
    except OSError as e:
        return False, "Could not reach the printer at %s:%s (%s)." % (host, port, e)
    return True, "Sent to the printer at %s:%s." % (host, port)


def email_configured():
    return bool((get_setting("smtp_host") or "").strip())


def send_email(to, subject, body):
    """Send an email through the configured SMTP server. Returns (ok, message)."""
    host = (get_setting("smtp_host") or "").strip()
    if not host:
        return False, "Email is not configured. Add your mail server on the LAN Setup screen."
    if not to:
        return False, "No recipient address."
    try:
        port = int((get_setting("smtp_port") or "25").strip() or 25)
    except ValueError:
        port = 25
    sender = (get_setting("smtp_from") or get_setting("smtp_user") or "ucscu@localhost").strip()
    user = (get_setting("smtp_user") or "").strip()
    password = get_setting("smtp_password") or ""
    use_tls = (get_setting("smtp_tls") or "") == "1"

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=PRINT_TIMEOUT) as smtp:
            if use_tls:
                smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
    except Exception as e:  # smtplib raises a wide range of errors
        return False, "Email failed: %s" % e
    return True, "Email sent to %s." % to
