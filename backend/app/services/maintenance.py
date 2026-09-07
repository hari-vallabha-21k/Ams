from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import CredentialStatus, DeliveryStatus, VisitorStatus
from app.models import Delivery, QrCredential, Visitor


def expire_passes(db: Session, now: datetime | None = None) -> dict[str, int]:
    """Mark passes whose window has closed as expired.

    Expiry is enforced at verification time regardless; this keeps the lists and
    reports honest for passes nobody ever presented.
    """
    now = now or datetime.utcnow()
    counts = {"visitors": 0, "deliveries": 0, "credentials": 0}

    for visitor in db.scalars(
        select(Visitor).where(
            Visitor.valid_until < now,
            Visitor.status.in_([VisitorStatus.SCHEDULED.value]),
        )
    ).all():
        visitor.status = VisitorStatus.EXPIRED.value
        counts["visitors"] += 1

    for delivery in db.scalars(
        select(Delivery).where(
            Delivery.valid_until < now,
            Delivery.status.in_([DeliveryStatus.SCHEDULED.value]),
        )
    ).all():
        delivery.status = DeliveryStatus.EXPIRED.value
        counts["deliveries"] += 1

    for credential in db.scalars(
        select(QrCredential).where(
            QrCredential.valid_until.is_not(None),
            QrCredential.valid_until < now,
            QrCredential.status == CredentialStatus.ACTIVE.value,
        )
    ).all():
        credential.status = CredentialStatus.EXPIRED.value
        counts["credentials"] += 1

    db.commit()
    return counts
