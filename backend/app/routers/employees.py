from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, get_current_user, require_admin, require_gate_staff
from app.enums import EmployeeStatus, Role, SubjectType
from app.models import AccessLog, AccessPolicy, Employee, User
from app.routers.common import log_out
from app.services import audit
from app.services import credentials as credential_service

router = APIRouter(prefix="/api/employees", tags=["employees"])


def _get_employee(db: Session, employee_id: int) -> Employee:
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


def _assert_can_view(user: User, employee: Employee) -> None:
    """Employees may only read their own record."""
    if user.role == Role.EMPLOYEE.value and user.employee_id != employee.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")


@router.get("", response_model=schemas.EmployeePage)
def list_employees(
    search: str | None = None,
    department: str | None = None,
    status_filter: EmployeeStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_gate_staff),
):
    query = select(Employee)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Employee.full_name).like(pattern),
                func.lower(Employee.employee_code).like(pattern),
                func.lower(func.coalesce(Employee.email, "")).like(pattern),
                func.lower(func.coalesce(Employee.phone, "")).like(pattern),
            )
        )
    if department:
        query = query.where(Employee.department == department)
    if status_filter:
        query = query.where(Employee.status == status_filter.value)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Employee.full_name).limit(limit).offset(offset)).all()
    return schemas.EmployeePage(total=total, limit=limit, offset=offset, items=list(items))


@router.post("", response_model=schemas.EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: schemas.EmployeeCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    if db.scalars(select(Employee).where(Employee.employee_code == payload.employee_code)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee ID already exists")
    employee = Employee(**payload.model_dump(exclude={"status"}), status=payload.status.value)
    db.add(employee)
    db.flush()
    audit.record(
        db,
        user=actor,
        action="CREATE_EMPLOYEE",
        entity="employee",
        entity_id=employee.id,
        ip_address=client_ip(request),
        meta={"employee_code": employee.employee_code},
    )
    db.commit()
    return employee


@router.get("/{employee_id}", response_model=schemas.EmployeeOut)
def get_employee(
    employee_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    employee = _get_employee(db, employee_id)
    _assert_can_view(user, employee)
    return employee


@router.put("/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(
    employee_id: int,
    payload: schemas.EmployeeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    employee = _get_employee(db, employee_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("status"):
        data["status"] = EmployeeStatus(data["status"]).value
    for field, value in data.items():
        setattr(employee, field, value)
    if data.get("status") and data["status"] != EmployeeStatus.ACTIVE.value:
        # A person who is no longer active must not keep a working credential.
        credential_service.revoke_existing(db, SubjectType.EMPLOYEE, employee.id)
    audit.record(
        db,
        user=actor,
        action="UPDATE_EMPLOYEE",
        entity="employee",
        entity_id=employee.id,
        ip_address=client_ip(request),
        meta=data,
    )
    db.commit()
    return employee


@router.delete("/{employee_id}", response_model=schemas.EmployeeOut)
def deactivate_employee(
    employee_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    """Employees are never deleted - the access history must stay intact."""
    employee = _get_employee(db, employee_id)
    employee.status = EmployeeStatus.INACTIVE.value
    credential_service.revoke_existing(db, SubjectType.EMPLOYEE, employee.id)
    audit.record(
        db,
        user=actor,
        action="DEACTIVATE_EMPLOYEE",
        entity="employee",
        entity_id=employee.id,
        ip_address=client_ip(request),
    )
    db.commit()
    return employee


@router.get("/{employee_id}/policies", response_model=list[schemas.AccessPolicyOut])
def employee_policies(
    employee_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    employee = _get_employee(db, employee_id)
    _assert_can_view(user, employee)
    return list(
        db.scalars(
            select(AccessPolicy).where(AccessPolicy.employee_id == employee.id).order_by(AccessPolicy.id)
        ).all()
    )


@router.get("/{employee_id}/access-logs", response_model=list[schemas.AccessLogOut])
def employee_access_logs(
    employee_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    employee = _get_employee(db, employee_id)
    _assert_can_view(user, employee)
    logs = db.scalars(
        select(AccessLog)
        .where(
            AccessLog.subject_type == SubjectType.EMPLOYEE.value,
            AccessLog.subject_id == employee.id,
        )
        .order_by(AccessLog.occurred_at.desc())
        .limit(limit)
    ).all()
    return [log_out(log, db) for log in logs]
