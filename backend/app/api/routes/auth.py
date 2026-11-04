from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter, user_or_ip_key
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
)
from app.services.identity import (
    issue_password_reset_token,
    issue_verification_token,
    reset_password,
    verify_email,
)
from app.services.mail import (
    MailBackend,
    deliver,
    get_mail_backend,
    password_reset_email,
    verification_email,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_settings = get_settings()

RESET_REQUESTED_MESSAGE = (
    "Si ese email tiene cuenta, te hemos enviado un enlace para restablecer la contraseña."
)
INVALID_VERIFICATION_LINK = "El enlace de verificación no es válido o ha caducado"
INVALID_RESET_LINK = "El enlace para restablecer la contraseña no es válido, ya se usó o ha caducado"


def _send_verification(background: BackgroundTasks, mail: MailBackend, user: User) -> None:
    message = verification_email(user.email, issue_verification_token(user), get_settings().frontend_base_url)
    background.add_task(deliver, mail, message)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(_settings.rate_limit_auth)
def register(
    request: Request,
    payload: UserRegister,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    mail: MailBackend = Depends(get_mail_backend),
) -> TokenResponse:
    user = User(
        email=payload.email,
        handle=payload.handle,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese email o handle ya está en uso",
        ) from exc
    db.refresh(user)
    _send_verification(background, mail, user)
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
@limiter.limit(_settings.rate_limit_auth)
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/verify", response_model=MessageResponse)
def verify(token: str = Query(min_length=1, max_length=2048), db: Session = Depends(get_db)) -> MessageResponse:
    user = verify_email(db, token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_VERIFICATION_LINK)
    db.commit()
    return MessageResponse(message="Email verificado. Ya puedes ganar Chispas.")


@router.post("/verify/resend", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(_settings.rate_limit_verification_resend, key_func=user_or_ip_key)
def resend_verification(
    request: Request,
    background: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    mail: MailBackend = Depends(get_mail_backend),
) -> MessageResponse:
    if current_user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tu email ya está verificado")
    _send_verification(background, mail, current_user)
    return MessageResponse(message="Te hemos enviado otro email de verificación.")


@router.post(
    "/password-reset/request", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit(_settings.rate_limit_password_reset)
def request_password_reset(
    request: Request,
    payload: PasswordResetRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    mail: MailBackend = Depends(get_mail_backend),
) -> MessageResponse:
    # Misma respuesta exista o no la cuenta: no se revela qué emails están registrados.
    user = db.query(User).filter(User.email == payload.email).first()
    if user is not None:
        message = password_reset_email(
            user.email, issue_password_reset_token(user), get_settings().frontend_base_url
        )
        background.add_task(deliver, mail, message)
    return MessageResponse(message=RESET_REQUESTED_MESSAGE)


@router.post("/password-reset/confirm", response_model=MessageResponse)
@limiter.limit(_settings.rate_limit_password_reset)
def confirm_password_reset(
    request: Request,
    payload: PasswordResetConfirm,
    db: Session = Depends(get_db),
) -> MessageResponse:
    user = reset_password(db, payload.token, payload.new_password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_RESET_LINK)
    db.commit()
    return MessageResponse(message="Contraseña cambiada. Ya puedes entrar con la nueva.")
