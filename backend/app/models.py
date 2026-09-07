from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Enum-like columns are stored as strings so the schema stays portable across
# PostgreSQL (production) and SQLite (tests).


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employee: Mapped["Employee | None"] = relationship(back_populates="user")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    designation: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    date_joined: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User | None"] = relationship(back_populates="employee", uselist=False)
    policies: Mapped[list["AccessPolicy"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class Gate(Base):
    __tablename__ = "gates"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AccessPolicy(Base):
    """Where and when an employee is allowed to pass a gate."""

    __tablename__ = "access_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    gate_id: Mapped[int] = mapped_column(ForeignKey("gates.id"), index=True)
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date] = mapped_column(Date)
    # ISO weekdays as a comma separated list: 1=Monday ... 7=Sunday
    days_of_week: Mapped[str] = mapped_column(String(32), default="1,2,3,4,5")
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employee: Mapped["Employee"] = relationship(back_populates="policies")
    gate: Mapped["Gate"] = relationship()


class Visitor(Base):
    __tablename__ = "visitors"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    host_employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    purpose: Mapped[str] = mapped_column(String(48))
    purpose_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    gate_id: Mapped[int] = mapped_column(ForeignKey("gates.id"), index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime)
    valid_until: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), default="SCHEDULED", index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    host: Mapped["Employee | None"] = relationship()
    gate: Mapped["Gate"] = relationship()


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    company: Mapped[str] = mapped_column(String(255), index=True)
    driver_name: Mapped[str] = mapped_column(String(255))
    driver_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    purpose: Mapped[str] = mapped_column(String(48))
    purpose_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    host_employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    gate_id: Mapped[int] = mapped_column(ForeignKey("gates.id"), index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime)
    valid_until: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), default="SCHEDULED", index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    host: Mapped["Employee | None"] = relationship()
    gate: Mapped["Gate"] = relationship()


class QrCredential(Base):
    """A QR credential holds only an opaque token; the record holds the meaning."""

    __tablename__ = "qr_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(16), index=True)
    subject_id: Mapped[int] = mapped_column(Integer, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Encrypted with the application secret so the pass can be shown again to
    # its owner; a database dump on its own yields no usable tokens.
    token_encrypted: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    gate_id: Mapped[int | None] = mapped_column(ForeignKey("gates.id"), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    issued_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    gate: Mapped["Gate | None"] = relationship()


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(16), index=True)
    subject_id: Mapped[int] = mapped_column(Integer, index=True)
    document_type: Mapped[str] = mapped_column(String(32))
    reference_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AccessLog(Base):
    """Append-only record of every access attempt."""

    __tablename__ = "access_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(16), index=True)
    subject_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    subject_label: Mapped[str] = mapped_column(String(255))
    subject_reference: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    credential_id: Mapped[int | None] = mapped_column(ForeignKey("qr_credentials.id"), nullable=True)
    gate_id: Mapped[int | None] = mapped_column(ForeignKey("gates.id"), index=True, nullable=True)
    direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    reason: Mapped[str | None] = mapped_column(String(48), nullable=True)
    reason_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(48), nullable=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)

    gate: Mapped["Gate | None"] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    user_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)


class Presence(Base):
    """One row per person currently inside the premises."""

    __tablename__ = "presence"
    __table_args__ = (UniqueConstraint("subject_type", "subject_id", name="uq_presence_subject"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(16), index=True)
    subject_id: Mapped[int] = mapped_column(Integer, index=True)
    subject_label: Mapped[str] = mapped_column(String(255))
    subject_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(48), nullable=True)
    host_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gate_id: Mapped[int | None] = mapped_column(ForeignKey("gates.id"), nullable=True)
    entered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expected_exit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    gate: Mapped["Gate | None"] = relationship()
