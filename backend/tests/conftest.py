import os
import tempfile

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_gate.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("STORAGE_DIR", tempfile.mkdtemp(prefix="gate-storage-"))
os.environ.setdefault("BOOTSTRAP_EMAIL", "bootstrap@system.local")

from datetime import date, datetime, time, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.enums import Purpose, Role, SubjectType  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AccessPolicy, Delivery, Employee, Gate, User, Visitor  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import credentials as credential_service  # noqa: E402

PASSWORD = "Password123!"


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def world(db):
    """A small company: two gates, one employee with a policy, and staff logins."""
    gate = Gate(code="G1", name="Main Entrance", location="North", status="ACTIVE")
    other_gate = Gate(code="G3", name="Warehouse", location="Rear", status="ACTIVE")
    db.add_all([gate, other_gate])
    db.flush()

    employee = Employee(
        employee_code="EMP1024", full_name="Anita Rao", department="Operations", status="ACTIVE"
    )
    db.add(employee)
    db.flush()

    db.add(
        AccessPolicy(
            employee_id=employee.id,
            gate_id=gate.id,
            valid_from=date.today() - timedelta(days=1),
            valid_until=date.today() + timedelta(days=365),
            days_of_week="1,2,3,4,5,6,7",
            start_time=time(0, 0),
            end_time=time(23, 59),
        )
    )
    _, employee_token = credential_service.issue(
        db, subject_type=SubjectType.EMPLOYEE, subject_id=employee.id
    )

    users = {
        Role.SUPER_ADMIN: User(
            email="root@company.com",
            full_name="Root",
            role=Role.SUPER_ADMIN.value,
            password_hash=hash_password(PASSWORD),
        ),
        Role.ADMIN: User(
            email="admin@company.com",
            full_name="Admin",
            role=Role.ADMIN.value,
            password_hash=hash_password(PASSWORD),
        ),
        Role.SECURITY_GUARD: User(
            email="guard@company.com",
            full_name="Guard",
            role=Role.SECURITY_GUARD.value,
            password_hash=hash_password(PASSWORD),
        ),
        Role.EMPLOYEE: User(
            email="anita@company.com",
            full_name="Anita Rao",
            role=Role.EMPLOYEE.value,
            password_hash=hash_password(PASSWORD),
            employee_id=employee.id,
        ),
    }
    db.add_all(list(users.values()))

    now = datetime.utcnow()
    delivery = Delivery(
        reference="DEL-2026-00001",
        company="ABC Suppliers",
        driver_name="Ravi Kumar",
        vehicle_number="TS09AB1234",
        purpose=Purpose.MATERIAL_DELIVERY.value,
        gate_id=gate.id,
        valid_from=now - timedelta(hours=1),
        valid_until=now + timedelta(hours=2),
    )
    visitor = Visitor(
        reference="VIS-2026-00001",
        full_name="John Smith",
        company="Northwind",
        purpose=Purpose.BUSINESS_MEETING.value,
        gate_id=gate.id,
        valid_from=now - timedelta(hours=1),
        valid_until=now + timedelta(hours=2),
    )
    db.add_all([delivery, visitor])
    db.flush()
    _, delivery_token = credential_service.issue(
        db,
        subject_type=SubjectType.DELIVERY,
        subject_id=delivery.id,
        gate_id=gate.id,
        valid_from=delivery.valid_from,
        valid_until=delivery.valid_until,
    )
    _, visitor_token = credential_service.issue(
        db,
        subject_type=SubjectType.VISITOR,
        subject_id=visitor.id,
        gate_id=gate.id,
        valid_from=visitor.valid_from,
        valid_until=visitor.valid_until,
    )
    db.commit()

    return {
        "gate": gate,
        "other_gate": other_gate,
        "employee": employee,
        "employee_token": employee_token,
        "delivery": delivery,
        "delivery_token": delivery_token,
        "visitor": visitor,
        "visitor_token": visitor_token,
        "users": users,
    }


@pytest.fixture()
def auth(client):
    def _login(email: str) -> dict[str, str]:
        response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login
