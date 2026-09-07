from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Delivery, Visitor


def next_delivery_reference(db: Session, now: datetime | None = None) -> str:
    """DEL-<year>-<zero padded sequence within the year>."""
    year = (now or datetime.utcnow()).year
    prefix = f"DEL-{year}-"
    count = db.scalar(
        select(func.count()).select_from(Delivery).where(Delivery.reference.like(f"{prefix}%"))
    )
    return f"{prefix}{(count or 0) + 1:05d}"


def next_visitor_reference(db: Session, now: datetime | None = None) -> str:
    year = (now or datetime.utcnow()).year
    prefix = f"VIS-{year}-"
    count = db.scalar(
        select(func.count()).select_from(Visitor).where(Visitor.reference.like(f"{prefix}%"))
    )
    return f"{prefix}{(count or 0) + 1:05d}"
