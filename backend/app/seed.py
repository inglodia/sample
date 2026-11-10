from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.deps import hash_password, verify_password
from app.models.user import User


def seed_admin(db: Session | None = None) -> None:
    owns_session = db is None
    session = db if db is not None else SessionLocal()
    try:
        email = settings.admin_email.strip().lower()
        existing = session.scalar(select(User).where(User.email == email))
        if existing is not None:
            # Keep local admin password in sync with ADMIN_PASSWORD from .env
            if not verify_password(settings.admin_password, existing.password_hash):
                existing.password_hash = hash_password(settings.admin_password)
            if existing.role != "admin":
                existing.role = "admin"
            if owns_session:
                session.commit()
            return
        session.add(
            User(
                email=email,
                password_hash=hash_password(settings.admin_password),
                full_name="Admin",
                role="admin",
            )
        )
        if owns_session:
            session.commit()
    except Exception:
        if owns_session:
            session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


if __name__ == "__main__":
    seed_admin()
