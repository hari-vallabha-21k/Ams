from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.enums import Role
from app.models import User
from app.security import hash_password


def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


def ensure_super_admin(db: Session) -> User | None:
    """Create the first super admin so the system can be logged into once."""
    if db.scalars(select(User).where(User.role == Role.SUPER_ADMIN.value)).first():
        return None
    user = User(
        email=settings.bootstrap_email.lower(),
        full_name="Super Admin",
        role=Role.SUPER_ADMIN.value,
        password_hash=hash_password(settings.bootstrap_password),
    )
    db.add(user)
    db.commit()
    return user


def initialise() -> None:
    create_schema()
    with SessionLocal() as db:
        ensure_super_admin(db)
