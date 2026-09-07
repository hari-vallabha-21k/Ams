"""Seed the database with a small, realistic demo data set.

Run with:  python -m app.seed
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select

from app.bootstrap import create_schema, ensure_super_admin
from app.db import SessionLocal
from app.enums import DocumentType, Purpose, Role, SubjectType
from app.models import AccessPolicy, Delivery, Document, Employee, Gate, User, Visitor
from app.security import hash_password
from app.services import credentials as credential_service
from app.services.references import next_delivery_reference, next_visitor_reference

DEMO_PASSWORD = "Password123!"


def run() -> None:
    create_schema()
    with SessionLocal() as db:
        ensure_super_admin(db)
        if db.scalars(select(Gate)).first():
            print("Database already seeded; nothing to do.")
            return

        gates = [
            Gate(code="G1", name="Main Entrance", location="North side", status="ACTIVE"),
            Gate(code="G2", name="Employee Entrance", location="East side", status="ACTIVE"),
            Gate(code="G3", name="Warehouse", location="Rear yard", status="ACTIVE"),
            Gate(code="G4", name="Parking", location="Basement", status="INACTIVE"),
        ]
        db.add_all(gates)
        db.flush()

        employees = [
            Employee(
                employee_code="EMP1024",
                full_name="Anita Rao",
                department="Operations",
                designation="Shift Manager",
                phone="9000000001",
                email="anita.rao@company.com",
                status="ACTIVE",
                date_joined=date(2024, 4, 1),
            ),
            Employee(
                employee_code="EMP1025",
                full_name="Vikram Shah",
                department="Stores",
                designation="Storekeeper",
                phone="9000000002",
                email="vikram.shah@company.com",
                status="ACTIVE",
                date_joined=date(2025, 1, 15),
            ),
            Employee(
                employee_code="EMP1026",
                full_name="Priya Menon",
                department="Human Resources",
                designation="HR Executive",
                phone="9000000003",
                email="priya.menon@company.com",
                status="INACTIVE",
                date_joined=date(2023, 7, 10),
            ),
        ]
        db.add_all(employees)
        db.flush()

        db.add_all(
            [
                User(
                    email="admin.desk@company.com",
                    full_name="Meera Desai",
                    role=Role.ADMIN.value,
                    password_hash=hash_password(DEMO_PASSWORD),
                ),
                User(
                    email="guard@company.com",
                    full_name="Suresh Patil",
                    role=Role.SECURITY_GUARD.value,
                    password_hash=hash_password(DEMO_PASSWORD),
                ),
                User(
                    email="anita.rao@company.com",
                    full_name="Anita Rao",
                    role=Role.EMPLOYEE.value,
                    password_hash=hash_password(DEMO_PASSWORD),
                    employee_id=employees[0].id,
                ),
            ]
        )

        for employee in employees[:2]:
            for gate in gates[:2]:
                db.add(
                    AccessPolicy(
                        employee_id=employee.id,
                        gate_id=gate.id,
                        valid_from=date.today() - timedelta(days=30),
                        valid_until=date.today() + timedelta(days=365),
                        days_of_week="1,2,3,4,5",
                        start_time=time(6, 0),
                        end_time=time(22, 0),
                    )
                )
            credential_service.issue(
                db, subject_type=SubjectType.EMPLOYEE, subject_id=employee.id
            )

        now = datetime.utcnow()
        delivery = Delivery(
            reference=next_delivery_reference(db),
            company="ABC Suppliers",
            driver_name="Ravi Kumar",
            driver_phone="9800000001",
            vehicle_number="TS09AB1234",
            purpose=Purpose.MATERIAL_DELIVERY.value,
            host_department="Stores",
            host_employee_id=employees[1].id,
            gate_id=gates[0].id,
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=6),
        )
        db.add(delivery)
        db.flush()
        _, delivery_token = credential_service.issue(
            db,
            subject_type=SubjectType.DELIVERY,
            subject_id=delivery.id,
            gate_id=delivery.gate_id,
            valid_from=delivery.valid_from,
            valid_until=delivery.valid_until,
        )
        db.add(
            Document(
                subject_type=SubjectType.DELIVERY.value,
                subject_id=delivery.id,
                document_type=DocumentType.INVOICE.value,
                reference_number="INV-82731",
                file_name="INV-82731.pdf",
                stored_path="./storage/seed/INV-82731.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
            )
        )

        visitor = Visitor(
            reference=next_visitor_reference(db),
            full_name="John Smith",
            company="Northwind Consulting",
            phone="9700000001",
            host_employee_id=employees[0].id,
            purpose=Purpose.BUSINESS_MEETING.value,
            gate_id=gates[0].id,
            valid_from=now - timedelta(minutes=30),
            valid_until=now + timedelta(hours=4),
        )
        db.add(visitor)
        db.flush()
        _, visitor_token = credential_service.issue(
            db,
            subject_type=SubjectType.VISITOR,
            subject_id=visitor.id,
            gate_id=visitor.gate_id,
            valid_from=visitor.valid_from,
            valid_until=visitor.valid_until,
        )
        db.commit()

        print("Seeded demo data.")
        print(f"  Admin login    : admin.desk@company.com / {DEMO_PASSWORD}")
        print(f"  Guard login    : guard@company.com / {DEMO_PASSWORD}")
        print(f"  Employee login : anita.rao@company.com / {DEMO_PASSWORD}")
        print(f"  Delivery pass  : /d/{delivery_token}  ({delivery.reference})")
        print(f"  Visitor pass   : /v/{visitor_token}  ({visitor.reference})")


if __name__ == "__main__":
    run()
