from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, require_super_admin
from app.enums import Role
from app.models import User
from app.security import hash_password
from app.services import audit

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_super_admin)])


@router.get("", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return list(db.scalars(select(User).order_by(User.id)).all())


@router.post("", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: schemas.UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    email = payload.email.lower().strip()
    if db.scalars(select(User).where(User.email == email)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=email,
        full_name=payload.full_name,
        role=payload.role.value,
        password_hash=hash_password(payload.password),
        employee_id=payload.employee_id,
    )
    db.add(user)
    db.flush()
    audit.record(
        db,
        user=actor,
        action="CREATE_USER",
        entity="user",
        entity_id=user.id,
        ip_address=client_ip(request),
        meta={"email": email, "role": payload.role.value},
    )
    db.commit()
    return user


@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == actor.id and payload.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate yourself")
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if password:
        user.password_hash = hash_password(password)
    if "role" in data and data["role"]:
        user.role = Role(data.pop("role")).value
    for field, value in data.items():
        setattr(user, field, value)
    audit.record(
        db,
        user=actor,
        action="UPDATE_USER",
        entity="user",
        entity_id=user.id,
        ip_address=client_ip(request),
        meta={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
    )
    db.commit()
    return user
