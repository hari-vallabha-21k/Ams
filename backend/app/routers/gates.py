from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, get_current_user, require_admin
from app.enums import GateStatus
from app.models import Gate, User
from app.services import audit

router = APIRouter(prefix="/api/gates", tags=["gates"])


@router.get("", response_model=list[schemas.GateOut])
def list_gates(
    status_filter: GateStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Gate).order_by(Gate.id)
    if status_filter:
        query = query.where(Gate.status == status_filter.value)
    return list(db.scalars(query).all())


@router.post("", response_model=schemas.GateOut, status_code=status.HTTP_201_CREATED)
def create_gate(
    payload: schemas.GateCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    if db.scalars(select(Gate).where(Gate.code == payload.code)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Gate code already exists")
    gate = Gate(**payload.model_dump(exclude={"status"}), status=payload.status.value)
    db.add(gate)
    db.flush()
    audit.record(db, user=actor, action="CREATE_GATE", entity="gate", entity_id=gate.id, ip_address=client_ip(request))
    db.commit()
    return gate


@router.get("/{gate_id}", response_model=schemas.GateOut)
def get_gate(gate_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    gate = db.get(Gate, gate_id)
    if not gate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")
    return gate


@router.put("/{gate_id}", response_model=schemas.GateOut)
def update_gate(
    gate_id: int,
    payload: schemas.GateUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    gate = db.get(Gate, gate_id)
    if not gate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("status"):
        data["status"] = GateStatus(data["status"]).value
    for field, value in data.items():
        setattr(gate, field, value)
    audit.record(
        db,
        user=actor,
        action="UPDATE_GATE",
        entity="gate",
        entity_id=gate.id,
        ip_address=client_ip(request),
        meta=data,
    )
    db.commit()
    return gate
