# utils/email_utils.py
import os
from email.message import EmailMessage
import smtplib
import logging

logger = logging.getLogger(__name__)

def send_email(recipients, subject, body):
    """Send a simple plaintext email via SMTP (Gmail example)."""
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = os.getenv('EMAIL_SENDER')
    msg['To'] = ', '.join(recipients)
    msg.set_content(body)

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(os.getenv('EMAIL_SENDER'), os.getenv('EMAIL_PASSWORD'))
            smtp.send_message(msg)
        logger.info("Email sent to %s", recipients)
    except Exception as e:
        logger.exception("Failed to send email: %s", e)
        raise
