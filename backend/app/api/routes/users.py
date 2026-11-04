from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter, user_or_ip_key
from app.db.session import get_db
from app.models.user import HandleVerificationStatus, User
from app.schemas.user import HandleVerificationOut, UserOut
from app.services.identity import HandleAlreadyVerified, request_handle_verification

router = APIRouter(prefix="/api/users", tags=["users"])

HANDLE_INSTRUCTIONS = (
    "Pon este código en la bio de tu cuenta de Instagram o TikTok. "
    "Lo revisaremos a mano y, una vez aprobado, podrás quitarlo."
)


def _pending_code(user: User) -> str | None:
    if user.handle_verification_status == HandleVerificationStatus.pending:
        return user.handle_verification_code
    return None


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        handle=current_user.handle,
        faction_slug=current_user.faction.slug if current_user.faction else None,
        role=current_user.role.value if current_user.role else None,
        chispas=current_user.chispas,
        is_verified=current_user.is_verified,
        handle_verification_status=current_user.handle_verification_status.value,
        handle_verification_code=_pending_code(current_user),
    )


@router.post(
    "/me/handle-verification",
    response_model=HandleVerificationOut,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(get_settings().rate_limit_handle_verification, key_func=user_or_ip_key)
def start_handle_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HandleVerificationOut:
    try:
        request_handle_verification(current_user)
    except HandleAlreadyVerified as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tu handle ya está verificado") from exc
    db.commit()
    return HandleVerificationOut(
        handle=current_user.handle,
        status=current_user.handle_verification_status.value,
        code=current_user.handle_verification_code,
        requested_at=current_user.handle_verification_requested_at,
        instructions=HANDLE_INSTRUCTIONS,
    )
