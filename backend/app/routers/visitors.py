from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, require_gate_staff
from app.enums import Purpose, SubjectType, VisitorStatus
from app.models import Employee, Gate, User, Visitor
from app.routers.common import visitor_out
from app.services import audit
from app.services import credentials as credential_service
from app.services.references import next_visitor_reference

router = APIRouter(prefix="/api/visitors", tags=["visitors"])


def _get_visitor(db: Session, visitor_id: int) -> Visitor:
    visitor = db.get(Visitor, visitor_id)
    if not visitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor not found")
    return visitor


@router.get("", response_model=schemas.VisitorPage)
def list_visitors(
    search: str | None = None,
    status_filter: VisitorStatus | None = None,
    gate_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_gate_staff),
):
    query = select(Visitor)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Visitor.full_name).like(pattern),
                func.lower(Visitor.reference).like(pattern),
                func.lower(func.coalesce(Visitor.company, "")).like(pattern),
                func.lower(func.coalesce(Visitor.phone, "")).like(pattern),
            )
        )
    if status_filter:
        query = query.where(Visitor.status == status_filter.value)
    if gate_id:
        query = query.where(Visitor.gate_id == gate_id)
    if date_from:
        query = query.where(Visitor.valid_until >= date_from)
    if date_to:
        query = query.where(Visitor.valid_from <= date_to)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Visitor.valid_from.desc()).limit(limit).offset(offset)).all()
    return schemas.VisitorPage(
        total=total, limit=limit, offset=offset, items=[visitor_out(v) for v in items]
    )


@router.post("", response_model=schemas.VisitorOut, status_code=status.HTTP_201_CREATED)
def create_visitor(
    payload: schemas.VisitorCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_gate_staff),
):
    if not db.get(Gate, payload.gate_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")
    if payload.host_employee_id and not db.get(Employee, payload.host_employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host employee not found")

    visitor = Visitor(
        **payload.model_dump(exclude={"purpose"}),
        purpose=payload.purpose.value,
        reference=next_visitor_reference(db),
        created_by=actor.id,
    )
    db.add(visitor)
    db.flush()
    credential_service.issue(
        db,
        subject_type=SubjectType.VISITOR,
        subject_id=visitor.id,
        gate_id=visitor.gate_id,
        valid_from=visitor.valid_from,
        valid_until=visitor.valid_until,
        issued_by=actor,
    )
    audit.record(
        db,
        user=actor,
        action="CREATE_VISITOR",
        entity="visitor",
        entity_id=visitor.id,
        ip_address=client_ip(request),
        meta={"reference": visitor.reference, "purpose": visitor.purpose},
    )
    db.commit()
    return visitor_out(visitor)


@router.get("/{visitor_id}", response_model=schemas.VisitorOut)
def get_visitor(visitor_id: int, db: Session = Depends(get_db), _: User = Depends(require_gate_staff)):
    return visitor_out(_get_visitor(db, visitor_id))


@router.put("/{visitor_id}", response_model=schemas.VisitorOut)
def update_visitor(
    visitor_id: int,
    payload: schemas.VisitorUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_gate_staff),
):
    visitor = _get_visitor(db, visitor_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("purpose"):
        data["purpose"] = Purpose(data["purpose"]).value
    if data.get("status"):
        data["status"] = VisitorStatus(data["status"]).value
    for field, value in data.items():
        setattr(visitor, field, value)
    if visitor.purpose == Purpose.OTHER.value and not visitor.purpose_description:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="purpose_description is required when purpose is OTHER",
        )
    credential = credential_service.active_credential(db, SubjectType.VISITOR, visitor.id)
    if credential:
        credential.gate_id = visitor.gate_id
        credential.valid_from = visitor.valid_from
        credential.valid_until = visitor.valid_until
    audit.record(
        db,
        user=actor,
        action="UPDATE_VISITOR",
        entity="visitor",
        entity_id=visitor.id,
        ip_address=client_ip(request),
        meta=data,
    )
    db.commit()
    return visitor_out(visitor)


@router.post("/{visitor_id}/cancel", response_model=schemas.VisitorOut)
def cancel_visitor(
    visitor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_gate_staff),
):
    visitor = _get_visitor(db, visitor_id)
    visitor.status = VisitorStatus.CANCELLED.value
    credential_service.revoke_existing(db, SubjectType.VISITOR, visitor.id)
    audit.record(
        db,
        user=actor,
        action="CANCEL_VISITOR",
        entity="visitor",
        entity_id=visitor.id,
        ip_address=client_ip(request),
    )
    db.commit()
    return visitor_out(visitor)
