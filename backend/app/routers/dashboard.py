from datetime import datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import require_gate_staff
from app.enums import AccessStatus, EmployeeStatus, GateStatus
from app.models import AccessLog, Delivery, Employee, Gate, Presence, User, Visitor
from app.routers.common import log_out

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardStats)
def dashboard(
    recent: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_gate_staff),
):
    today = datetime.utcnow().date()
    start, end = datetime.combine(today, time.min), datetime.combine(today, time.max)

    def count(model, *conditions) -> int:
        return db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0

    logs = db.scalars(
        select(AccessLog).order_by(AccessLog.occurred_at.desc(), AccessLog.id.desc()).limit(recent)
    ).all()

    return schemas.DashboardStats(
        employees=count(Employee, Employee.status == EmployeeStatus.ACTIVE.value),
        visitors_today=count(Visitor, Visitor.valid_from.between(start, end)),
        deliveries_today=count(Delivery, Delivery.valid_from.between(start, end)),
        currently_inside=db.scalar(select(func.count()).select_from(Presence)) or 0,
        denied_today=count(
            AccessLog,
            AccessLog.status == AccessStatus.DENIED.value,
            AccessLog.occurred_at.between(start, end),
        ),
        granted_today=count(
            AccessLog,
            AccessLog.status == AccessStatus.GRANTED.value,
            AccessLog.occurred_at.between(start, end),
        ),
        active_gates=count(Gate, Gate.status == GateStatus.ACTIVE.value),
        recent_activity=[log_out(log, db) for log in logs],
    )
