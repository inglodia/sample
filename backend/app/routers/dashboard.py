from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardStats, SignupDay

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStats:
    now = datetime.now(UTC)
    since_30d = now - timedelta(days=30)

    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    new_users_30d = (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.created_at >= since_30d)
        )
        or 0
    )
    admin_count = (
        db.scalar(
            select(func.count()).select_from(User).where(User.role == "admin")
        )
        or 0
    )
    user_count = (
        db.scalar(
            select(func.count()).select_from(User).where(User.role == "user")
        )
        or 0
    )

    day_col = func.date_trunc("day", User.created_at)
    rows = db.execute(
        select(day_col, func.count())
        .select_from(User)
        .where(User.created_at >= since_30d)
        .group_by(day_col)
        .order_by(day_col)
    ).all()

    signups_by_day: list[SignupDay] = []
    for day, count in rows:
        if day is None:
            continue
        d = day.date() if hasattr(day, "date") else day
        signups_by_day.append(
            SignupDay(date=d.isoformat() if hasattr(d, "isoformat") else str(d), count=count)
        )

    return DashboardStats(
        total_users=total_users,
        new_users_30d=new_users_30d,
        admin_count=admin_count,
        user_count=user_count,
        signups_by_day=signups_by_day,
    )
