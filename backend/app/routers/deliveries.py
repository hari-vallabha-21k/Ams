from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, require_gate_staff
from app.enums import DeliveryStatus, Purpose, SubjectType
from app.models import Delivery, Document, Employee, Gate, User
from app.routers.common import delivery_out
from app.services import audit
from app.services import credentials as credential_service
from app.services.references import next_delivery_reference

router = APIRouter(prefix="/api/deliveries", tags=["deliveries"])


def _get_delivery(db: Session, delivery_id: int) -> Delivery:
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    return delivery


@router.get("", response_model=schemas.DeliveryPage)
def list_deliveries(
    search: str | None = None,
    status_filter: DeliveryStatus | None = None,
    gate_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_gate_staff),
):
    query = select(Delivery)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Delivery.reference).like(pattern),
                func.lower(Delivery.company).like(pattern),
                func.lower(Delivery.driver_name).like(pattern),
                func.lower(func.coalesce(Delivery.vehicle_number, "")).like(pattern),
                func.lower(func.coalesce(Delivery.driver_phone, "")).like(pattern),
            )
        )
    if status_filter:
        query = query.where(Delivery.status == status_filter.value)
    if gate_id:
        query = query.where(Delivery.gate_id == gate_id)
    if date_from:
        query = query.where(Delivery.valid_until >= date_from)
    if date_to:
        query = query.where(Delivery.valid_from <= date_to)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Delivery.valid_from.desc()).limit(limit).offset(offset)).all()
    return schemas.DeliveryPage(
        total=total, limit=limit, offset=offset, items=[delivery_out(d) for d in items]
    )


@router.post("", response_model=schemas.DeliveryOut, status_code=status.HTTP_201_CREATED)
def create_delivery(
    payload: schemas.DeliveryCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_gate_staff),
):
    if not db.get(Gate, payload.gate_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")
    if payload.host_employee_id and not db.get(Employee, payload.host_employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host employee not found")

    delivery = Delivery(
        **payload.model_dump(exclude={"purpose"}),
        purpose=payload.purpose.value,
        reference=next_delivery_reference(db),
        created_by=actor.id,
    )
    db.add(delivery)
    db.flush()
    credential_service.issue(
        db,
        subject_type=SubjectType.DELIVERY,
        subject_id=delivery.id,
        gate_id=delivery.gate_id,
        valid_from=delivery.valid_from,
        valid_until=delivery.valid_until,
        issued_by=actor,
    )
    audit.record(
        db,
        user=actor,
        action="CREATE_DELIVERY",
        entity="delivery",
        entity_id=delivery.id,
        ip_address=client_ip(request),
        meta={"reference": delivery.reference, "company": delivery.company},
    )
    db.commit()
    return delivery_out(delivery)


@router.get("/{delivery_id}", response_model=schemas.DeliveryOut)
def get_delivery(
    delivery_id: int, db: Session = Depends(get_db), _: User = Depends(require_gate_staff)
):
    return delivery_out(_get_delivery(db, delivery_id))


@router.put("/{delivery_id}", response_model=schemas.DeliveryOut)
def update_delivery(
    delivery_id: int,
    payload: schemas.DeliveryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_gate_staff),
):
    delivery = _get_delivery(db, delivery_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("purpose"):
        data["purpose"] = Purpose(data["purpose"]).value
    if data.get("status"):
        data["status"] = DeliveryStatus(data["status"]).value
    for field, value in data.items():
        setattr(delivery, field, value)
    if delivery.purpose == Purpose.OTHER.value and not delivery.purpose_description:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="purpose_description is required when purpose is OTHER",
        )
    credential = credential_service.active_credential(db, SubjectType.DELIVERY, delivery.id)
    if credential:
        credential.gate_id = delivery.gate_id
        credential.valid_from = delivery.valid_from
        credential.valid_until = delivery.valid_until
    audit.record(
        db,
        user=actor,
        action="UPDATE_DELIVERY",
        entity="delivery",
        entity_id=delivery.id,
        ip_address=client_ip(request),
        meta=data,
    )
    db.commit()
    return delivery_out(delivery)


@router.post("/{delivery_id}/revoke", response_model=schemas.DeliveryOut)
def revoke_delivery(
    delivery_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_gate_staff),
):
    """Cancel the delivery and kill its pass in one step."""
    delivery = _get_delivery(db, delivery_id)
    delivery.status = DeliveryStatus.CANCELLED.value
    credential_service.revoke_existing(db, SubjectType.DELIVERY, delivery.id)
    audit.record(
        db,
        user=actor,
        action="CANCEL_DELIVERY",
        entity="delivery",
        entity_id=delivery.id,
        ip_address=client_ip(request),
    )
    db.commit()
    return delivery_out(delivery)


@router.get("/{delivery_id}/documents", response_model=list[schemas.DocumentOut])
def delivery_documents(
    delivery_id: int, db: Session = Depends(get_db), _: User = Depends(require_gate_staff)
):
    _get_delivery(db, delivery_id)
    return list(
        db.scalars(
            select(Document)
            .where(
                Document.subject_type == SubjectType.DELIVERY.value,
                Document.subject_id == delivery_id,
            )
            .order_by(Document.id)
        ).all()
    )
