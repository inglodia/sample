import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.user import User
from app.schemas.auth import UserOut
from app.schemas.user import RolePatchIn, UserListOut

router = APIRouter()


@router.get("", response_model=UserListOut)
def list_users(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserListOut:
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return UserListOut(items=[UserOut.model_validate(u) for u in users])


@router.patch("/{user_id}/role", response_model=UserOut)
def patch_user_role(
    user_id: uuid.UUID,
    body: RolePatchIn,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = body.role
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user
