from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, require_admin, require_gate_staff
from app.models import AccessPolicy, Employee, Gate, User
from app.services import audit

router = APIRouter(prefix="/api/access-policies", tags=["access-policies"])


@router.get("", response_model=list[schemas.AccessPolicyOut])
def list_policies(
    employee_id: int | None = None,
    gate_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_gate_staff),
):
    query = select(AccessPolicy)
    if employee_id:
        query = query.where(AccessPolicy.employee_id == employee_id)
    if gate_id:
        query = query.where(AccessPolicy.gate_id == gate_id)
    return list(db.scalars(query.order_by(AccessPolicy.id)).all())


@router.post("", response_model=schemas.AccessPolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: schemas.AccessPolicyCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    if not db.get(Employee, payload.employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    if not db.get(Gate, payload.gate_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")
    policy = AccessPolicy(
        **payload.model_dump(exclude={"days_of_week"}),
        days_of_week=",".join(str(d) for d in payload.days_of_week),
    )
    db.add(policy)
    db.flush()
    audit.record(
        db,
        user=actor,
        action="CREATE_ACCESS_POLICY",
        entity="access_policy",
        entity_id=policy.id,
        ip_address=client_ip(request),
        meta={"employee_id": policy.employee_id, "gate_id": policy.gate_id},
    )
    db.commit()
    return policy


@router.put("/{policy_id}", response_model=schemas.AccessPolicyOut)
def update_policy(
    policy_id: int,
    payload: schemas.AccessPolicyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    policy = db.get(AccessPolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access policy not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("days_of_week"):
        data["days_of_week"] = ",".join(str(d) for d in data["days_of_week"])
    for field, value in data.items():
        setattr(policy, field, value)
    audit.record(
        db,
        user=actor,
        action="UPDATE_ACCESS_POLICY",
        entity="access_policy",
        entity_id=policy.id,
        ip_address=client_ip(request),
        meta=data,
    )
    db.commit()
    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    policy = db.get(AccessPolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access policy not found")
    db.delete(policy)
    audit.record(
        db,
        user=actor,
        action="DELETE_ACCESS_POLICY",
        entity="access_policy",
        entity_id=policy_id,
        ip_address=client_ip(request),
    )
    db.commit()
