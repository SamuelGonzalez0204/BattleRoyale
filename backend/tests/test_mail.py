"""Unitarios del servicio de correo y sus backends."""

import logging
from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.services.mail import (
    ConsoleMailBackend,
    EmailMessage,
    SmtpMailBackend,
    build_backend,
    password_reset_email,
    verification_email,
)


def test_verification_email_contains_frontend_link() -> None:
    message = verification_email("a@example.com", "TOKEN123", "http://front.local")

    assert message.to == "a@example.com"
    assert "http://front.local/verificar.html?token=TOKEN123" in message.body


def test_password_reset_email_contains_frontend_link() -> None:
    message = password_reset_email("a@example.com", "TOKEN456", "http://front.local/")

    assert "http://front.local/recuperar.html?token=TOKEN456" in message.body


def test_console_backend_logs_the_message(caplog) -> None:
    message = EmailMessage(to="a@example.com", subject="Hola", body="enlace: http://x")

    with caplog.at_level(logging.INFO, logger="el_ciclo.mail"):
        ConsoleMailBackend().send(message)

    assert "a@example.com" in caplog.text
    assert "http://x" in caplog.text


def test_build_backend_defaults_to_console() -> None:
    assert isinstance(build_backend(Settings()), ConsoleMailBackend)


def test_build_backend_smtp() -> None:
    settings = Settings(mail_backend="smtp", smtp_host="smtp.test.local")

    assert isinstance(build_backend(settings), SmtpMailBackend)


def test_smtp_backend_sends_with_starttls_and_login() -> None:
    backend = SmtpMailBackend(
        host="smtp.test.local", port=587, user="u", password="p", sender="no-reply@example.com", starttls=True
    )
    message = EmailMessage(to="a@example.com", subject="Hola", body="cuerpo")

    with patch("app.services.mail.smtplib.SMTP") as smtp_cls:
        server = MagicMock()
        smtp_cls.return_value.__enter__.return_value = server
        backend.send(message)

    smtp_cls.assert_called_once_with("smtp.test.local", 587, timeout=10)
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("u", "p")
    sent = server.send_message.call_args.args[0]
    assert sent["To"] == "a@example.com"
    assert sent["From"] == "no-reply@example.com"
