"""Envío de correo transaccional por SMTP.

En desarrollo apunta a Mailpit, que captura los mensajes sin enviarlos a
destinatarios reales: se consultan en http://localhost:8025.
"""

import smtplib
from email.message import EmailMessage
from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MailSender:
    """Cliente SMTP para correo transaccional."""

    def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> bool:
        """Envía un correo. Devuelve si se entregó al servidor SMTP.

        Un fallo de correo nunca debe tumbar la operación que lo originó: si el
        servidor no responde, el registro o el pedido ya ocurrieron y deben
        completarse igual. Se registra el error y se continúa.
        """
        message = EmailMessage()
        message["From"] = f"{settings.mail_from_name} <{settings.mail_from}>"
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                if settings.smtp_tls:
                    smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            logger.error("mail_send_failed", to=to, subject=subject, error=str(exc))
            return False

        logger.info("mail_sent", to=to, subject=subject)
        return True


@lru_cache
def get_mail_sender() -> MailSender:
    return MailSender()
