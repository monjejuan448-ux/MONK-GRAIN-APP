"""Envío de correo transaccional."""

from app.integrations.mail.sender import MailSender, get_mail_sender

__all__ = ["MailSender", "get_mail_sender"]
