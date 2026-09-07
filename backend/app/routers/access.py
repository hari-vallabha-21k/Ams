from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, rate_limit_verification, require_gate_staff
from app.enums import AccessStatus, DenialReason, Direction, SubjectType
from app.models import AccessLog, AuditLog, Delivery, Presence, User, Visitor
from app.routers.common import log_out, presence_out, verification_out
from app.services import access_engine, audit

router = APIRouter(prefix="/api/access", tags=["access"])


@router.post(
    "/verify",
    response_model=schemas.VerifyResponse,
    dependencies=[Depends(rate_limit_verification)],
)
def verify(
    payload: schemas.VerifyRequest,
    db: Session = Depends(get_db),
    guard: User = Depends(require_gate_staff),
):
    """Run every access check and show the guard what the system found.

    This call never opens a gate; it only reports. The decision is recorded by
    /grant or /deny.
    """
    result = access_engine.verify(
        db, token=payload.token, gate_id=payload.gate_id, direction=payload.direction
    )
    return verification_out(result)


def _decide(
    db: Session,
    request: Request,
    guard: User,
    *,
    token: str,
    gate_id: int,
    direction: Direction,
    granted: bool,
    reason: DenialReason | None = None,
    reason_note: str | None = None,
    document_id: int | None = None,
) -> schemas.DecisionResponse:
    result = access_engine.verify(db, token=token, gate_id=gate_id, direction=direction)
    if granted and not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Access cannot be granted: {result.message}",
        )
    log = access_engine.record_decision(
        db,
        verification=result,
        granted=granted,
        guard=guard,
        reason=reason or (None if granted else result.denial_reason),
        reason_note=reason_note,
        document_id=document_id,
    )
    audit.record(
        db,
        user=guard,
        action="GRANT_ACCESS" if granted else "DENY_ACCESS",
        entity="access_log",
        entity_id=log.id,
        ip_address=client_ip(request),
        meta={
            "subject": log.subject_label,
            "reference": log.subject_reference,
            "gate_id": gate_id,
            "direction": direction.value,
            "reason": log.reason,
        },
    )
    db.commit()
    return schemas.DecisionResponse(log=log_out(log, db), verification=verification_out(result))


@router.post("/grant", response_model=schemas.DecisionResponse, dependencies=[Depends(rate_limit_verification)])
def grant(
    payload: schemas.DecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    guard: User = Depends(require_gate_staff),
):
    return _decide(
        db,
        request,
        guard,
        token=payload.token,
        gate_id=payload.gate_id,
        direction=payload.direction,
        granted=True,
        document_id=payload.document_id,
    )


@router.post("/entry", response_model=schemas.DecisionResponse, dependencies=[Depends(rate_limit_verification)])
def entry(
    payload: schemas.DecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    guard: User = Depends(require_gate_staff),
):
    return _decide(
        db,
        request,
        guard,
        token=payload.token,
        gate_id=payload.gate_id,
        direction=Direction.ENTRY,
        granted=True,
        document_id=payload.document_id,
    )


@router.post("/exit", response_model=schemas.DecisionResponse, dependencies=[Depends(rate_limit_verification)])
def exit_(
    payload: schemas.DecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    guard: User = Depends(require_gate_staff),
):
    return _decide(
        db,
        request,
        guard,
        token=payload.token,
        gate_id=payload.gate_id,
        direction=Direction.EXIT,
        granted=True,
        document_id=payload.document_id,
    )


@router.post("/deny", response_model=schemas.DecisionResponse, dependencies=[Depends(rate_limit_verification)])
def deny(
    payload: schemas.DenyRequest,
    request: Request,
    db: Session = Depends(get_db),
    guard: User = Depends(require_gate_staff),
):
    return _decide(
        db,
        request,
        guard,
        token=payload.token,
        gate_id=payload.gate_id,
        direction=payload.direction,
        granted=False,
        reason=payload.reason,
        reason_note=payload.reason_note,
    )


@router.get("/logs", response_model=schemas.AccessLogPage)
def logs(
    search: str | None = None,
    subject_type: SubjectType | None = None,
    status_filter: AccessStatus | None = None,
    gate_id: int | None = None,
    direction: Direction | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_gate_staff),
):
    query = select(AccessLog)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(AccessLog.subject_label).like(pattern),
                func.lower(func.coalesce(AccessLog.subject_reference, "")).like(pattern),
            )
        )
    if subject_type:
        query = query.where(AccessLog.subject_type == subject_type.value)
    if status_filter:
        query = query.where(AccessLog.status == status_filter.value)
    if gate_id:
        query = query.where(AccessLog.gate_id == gate_id)
    if direction:
        query = query.where(AccessLog.direction == direction.value)
    if date_from:
        query = query.where(AccessLog.occurred_at >= date_from)
    if date_to:
        query = query.where(AccessLog.occurred_at <= date_to)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(AccessLog.occurred_at.desc(), AccessLog.id.desc()).limit(limit).offset(offset)).all()
    return schemas.AccessLogPage(
        total=total, limit=limit, offset=offset, items=[log_out(log, db) for log in items]
    )


@router.get("/currently-inside", response_model=schemas.CurrentlyInside)
def currently_inside(db: Session = Depends(get_db), _: User = Depends(require_gate_staff)):
    people = list(db.scalars(select(Presence).order_by(Presence.entered_at)).all())
    counts = {t.value: 0 for t in SubjectType}
    for person in people:
        counts[person.subject_type] += 1
    return schemas.CurrentlyInside(
        total=len(people),
        employees=counts[SubjectType.EMPLOYEE.value],
        visitors=counts[SubjectType.VISITOR.value],
        delivery=counts[SubjectType.DELIVERY.value],
        people=[presence_out(p) for p in people],
    )


@router.get("/history/{reference}")
def history(reference: str, db: Session = Depends(get_db), _: User = Depends(require_gate_staff)):
    """Full trail for one pass reference, e.g. DEL-2026-00421."""
    reference = reference.strip()
    delivery = db.scalars(select(Delivery).where(Delivery.reference == reference)).first()
    visitor = db.scalars(select(Visitor).where(Visitor.reference == reference)).first()
    if not delivery and not visitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")

    subject_type = SubjectType.DELIVERY if delivery else SubjectType.VISITOR
    subject = delivery or visitor
    access_logs = db.scalars(
        select(AccessLog)
        .where(
            AccessLog.subject_type == subject_type.value,
            AccessLog.subject_id == subject.id,
        )
        .order_by(AccessLog.occurred_at)
    ).all()
    audit_entries = db.scalars(
        select(AuditLog)
        .where(AuditLog.entity.in_(["delivery", "visitor"]), AuditLog.entity_id == str(subject.id))
        .order_by(AuditLog.created_at)
    ).all()
    return {
        "reference": reference,
        "type": subject_type.value,
        "status": subject.status,
        "access_logs": [log_out(log, db) for log in access_logs],
        "audit_trail": [schemas.AuditLogOut.model_validate(a) for a in audit_entries],
    }
