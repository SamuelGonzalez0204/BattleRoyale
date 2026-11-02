from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


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
    )
