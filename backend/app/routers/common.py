from sqlalchemy.orm import Session

from app import schemas
from app.models import AccessLog, Delivery, Presence, User, Visitor
from app.services.access_engine import Verification


def visitor_out(visitor: Visitor) -> schemas.VisitorOut:
    data = schemas.VisitorOut.model_validate(visitor)
    data.host_name = visitor.host.full_name if visitor.host else None
    data.gate_name = visitor.gate.name if visitor.gate else None
    return data


def delivery_out(delivery: Delivery) -> schemas.DeliveryOut:
    data = schemas.DeliveryOut.model_validate(delivery)
    data.host_name = delivery.host.full_name if delivery.host else None
    data.gate_name = delivery.gate.name if delivery.gate else None
    return data


def log_out(log: AccessLog, db: Session | None = None) -> schemas.AccessLogOut:
    data = schemas.AccessLogOut.model_validate(log)
    data.gate_name = log.gate.name if log.gate else None
    if db is not None and log.verified_by:
        user = db.get(User, log.verified_by)
        data.verified_by_name = user.full_name if user else None
    return data


def presence_out(presence: Presence) -> schemas.PresenceOut:
    data = schemas.PresenceOut.model_validate(presence)
    data.gate_name = presence.gate.name if presence.gate else None
    return data


def verification_out(verification: Verification) -> schemas.VerifyResponse:
    return schemas.VerifyResponse(
        allowed=verification.allowed,
        message=verification.message,
        direction=verification.direction,
        gate=schemas.GateOut.model_validate(verification.gate) if verification.gate else None,
        subject=schemas.SubjectOut(**vars(verification.subject)) if verification.subject else None,
        checks=[schemas.CheckOut(**{k: v for k, v in vars(c).items() if k != "reason"}) for c in verification.checks],
        documents=[schemas.DocumentOut.model_validate(d) for d in verification.documents],
        suggested_denial_reason=verification.denial_reason,
        already_inside=verification.inside,
    )
