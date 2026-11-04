"""Envío de correo con backend intercambiable (console en desarrollo, smtp en producción)."""

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from typing import Protocol

from app.core.config import Settings, get_settings

logger = logging.getLogger("el_ciclo.mail")

SMTP_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class MailBackend(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class ConsoleMailBackend:
    """SOLO PARA DESARROLLO: escribe el correo (enlace con token incluido) en el log
    para poder copiar el enlace sin servidor SMTP. Nunca usarlo en producción."""

    def send(self, message: EmailMessage) -> None:
        logger.info("[mail:console] Para: %s | Asunto: %s\n%s", message.to, message.subject, message.body)


@dataclass(frozen=True)
class SmtpMailBackend:
    host: str
    port: int
    user: str
    password: str
    sender: str
    starttls: bool = True

    def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = self.sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.body)

        with smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT_SECONDS) as server:
            if self.starttls:
                server.starttls()
            if self.user:
                server.login(self.user, self.password)
            server.send_message(mime)


def build_backend(settings: Settings) -> MailBackend:
    if settings.mail_backend == "smtp":
        return SmtpMailBackend(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password,
            sender=settings.smtp_from,
            starttls=settings.smtp_starttls,
        )
    if settings.mail_backend == "console":
        return ConsoleMailBackend()
    raise ValueError(f"MAIL_BACKEND desconocido: {settings.mail_backend!r}")


def get_mail_backend() -> MailBackend:
    """Dependencia de FastAPI (los tests la sobrescriben con un buzón en memoria)."""
    return build_backend(get_settings())


def deliver(backend: MailBackend, message: EmailMessage) -> None:
    """Envía sin propagar errores: se ejecuta como BackgroundTask tras responder."""
    try:
        backend.send(message)
    except Exception:
        # No se loguea el cuerpo: contiene el token.
        logger.exception("No se pudo enviar el correo '%s' a %s", message.subject, message.to)


def _link(base_url: str, page: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/{page}?token={token}"


def verification_email(to: str, token: str, base_url: str) -> EmailMessage:
    link = _link(base_url, "verificar.html", token)
    return EmailMessage(
        to=to,
        subject="Confirma tu email en El Ciclo",
        body=(
            "¡Bienvenida/o a El Ciclo!\n\n"
            f"Confirma tu email abriendo este enlace:\n{link}\n\n"
            "Hasta que lo confirmes no podrás ganar Chispas.\n"
            "Si no creaste esta cuenta, ignora este mensaje."
        ),
    )


def password_reset_email(to: str, token: str, base_url: str) -> EmailMessage:
    link = _link(base_url, "recuperar.html", token)
    return EmailMessage(
        to=to,
        subject="Restablece tu contraseña de El Ciclo",
        body=(
            "Alguien (esperamos que tú) pidió restablecer tu contraseña.\n\n"
            f"Elige una nueva aquí:\n{link}\n\n"
            "El enlace caduca pronto y solo sirve una vez.\n"
            "Si no lo pediste, ignora este mensaje: tu contraseña no cambia."
        ),
    )
