"""The access engine.

The QR code is only an identifier. Every access decision is made here, from the
database record the token resolves to - never from the contents of the QR.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import (
    DOCUMENT_REQUIRED_PURPOSES,
    AccessStatus,
    CredentialStatus,
    DeliveryStatus,
    DenialReason,
    Direction,
    EmployeeStatus,
    GateStatus,
    Purpose,
    SubjectType,
    VisitorStatus,
)
from app.models import (
    AccessLog,
    AccessPolicy,
    Delivery,
    Document,
    Employee,
    Gate,
    Presence,
    QrCredential,
    User,
    Visitor,
)
from app.services import credentials as credential_service


@dataclass
class Check:
    code: str
    label: str
    passed: bool
    detail: str | None = None
    reason: DenialReason | None = None


@dataclass
class Subject:
    """Everything the guard needs to see on screen about who is at the gate."""

    type: SubjectType
    id: int | None
    label: str
    reference: str | None = None
    purpose: str | None = None
    purpose_description: str | None = None
    details: dict = field(default_factory=dict)


@dataclass
class Verification:
    allowed: bool
    checks: list[Check]
    subject: Subject | None
    credential: QrCredential | None
    gate: Gate | None
    direction: Direction
    documents: list[Document] = field(default_factory=list)
    denial_reason: DenialReason | None = None
    message: str = ""
    inside: bool = False

    @property
    def failed_checks(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]


def _weekday_allowed(policy: AccessPolicy, moment: datetime) -> bool:
    days = {d.strip() for d in policy.days_of_week.split(",") if d.strip()}
    return str(moment.isoweekday()) in days


def _presence(db: Session, subject_type: SubjectType, subject_id: int) -> Presence | None:
    return db.scalars(
        select(Presence).where(
            Presence.subject_type == subject_type.value, Presence.subject_id == subject_id
        )
    ).first()


def _documents(db: Session, subject_type: SubjectType, subject_id: int) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.subject_type == subject_type.value, Document.subject_id == subject_id)
            .order_by(Document.id)
        ).all()
    )


def _denied(checks: list[Check], **kwargs) -> Verification:
    failed = next((c for c in checks if not c.passed), None)
    return Verification(
        allowed=False,
        checks=checks,
        denial_reason=failed.reason if failed else DenialReason.OTHER,
        message=failed.detail or failed.label if failed else "Access denied",
        **kwargs,
    )


def verify(
    db: Session,
    *,
    token: str,
    gate_id: int,
    direction: Direction = Direction.ENTRY,
    now: datetime | None = None,
) -> Verification:
    now = now or datetime.utcnow()
    checks: list[Check] = []
    gate = db.get(Gate, gate_id)

    credential = credential_service.find_by_token(db, token)
    if credential is None:
        checks.append(
            Check("credential", "QR recognised", False, "QR code not recognised", DenialReason.INVALID_QR)
        )
        return _denied(checks, subject=None, credential=None, gate=gate, direction=direction)
    checks.append(Check("credential", "QR recognised", True))

    if gate is None:
        checks.append(Check("gate_exists", "Gate exists", False, "Unknown gate", DenialReason.WRONG_GATE))
        return _denied(checks, subject=None, credential=credential, gate=None, direction=direction)
    if gate.status != GateStatus.ACTIVE.value:
        checks.append(
            Check("gate_active", "Gate active", False, f"{gate.name} is inactive", DenialReason.WRONG_GATE)
        )
        return _denied(checks, subject=None, credential=credential, gate=gate, direction=direction)

    subject_type = SubjectType(credential.subject_type)

    # Credential status
    if credential.status == CredentialStatus.REVOKED.value:
        checks.append(
            Check("credential_status", "Credential active", False, "Credential revoked", DenialReason.REVOKED_QR)
        )
    elif credential.status in (
        CredentialStatus.EXPIRED.value,
        CredentialStatus.COMPLETED.value,
        CredentialStatus.USED.value,
    ):
        checks.append(
            Check(
                "credential_status",
                "Credential active",
                False,
                f"Credential {credential.status.lower()}",
                DenialReason.EXPIRED_QR,
            )
        )
    else:
        checks.append(Check("credential_status", "Credential active", True))

    # Credential validity window
    if credential.valid_from and now < credential.valid_from:
        checks.append(
            Check(
                "credential_window",
                "Credential in validity window",
                False,
                f"Not valid before {credential.valid_from:%d/%m/%Y %H:%M}",
                DenialReason.OUTSIDE_ALLOWED_TIME,
            )
        )
    elif credential.valid_until and now > credential.valid_until:
        checks.append(
            Check(
                "credential_window",
                "Credential in validity window",
                False,
                f"Expired at {credential.valid_until:%d/%m/%Y %H:%M}",
                DenialReason.EXPIRED_QR,
            )
        )
    else:
        checks.append(Check("credential_window", "Credential in validity window", True))

    if subject_type is SubjectType.EMPLOYEE:
        subject, extra, documents = _verify_employee(db, credential, gate, now)
    elif subject_type is SubjectType.VISITOR:
        subject, extra, documents = _verify_visitor(db, credential, gate, now)
    else:
        subject, extra, documents = _verify_delivery(db, credential, gate, now)
    checks.extend(extra)

    inside = False
    if subject and subject.id is not None:
        inside = _presence(db, subject_type, subject.id) is not None
        if direction is Direction.ENTRY and inside:
            checks.append(
                Check(
                    "direction",
                    "Not already inside",
                    False,
                    "Already recorded as inside the premises",
                    DenialReason.ALREADY_INSIDE,
                )
            )
        elif direction is Direction.EXIT and not inside:
            checks.append(
                Check(
                    "direction",
                    "Recorded as inside",
                    False,
                    "No open entry found for this person",
                    DenialReason.NOT_INSIDE,
                )
            )
        else:
            checks.append(
                Check(
                    "direction",
                    "Not already inside" if direction is Direction.ENTRY else "Recorded as inside",
                    True,
                )
            )

    if any(not c.passed for c in checks):
        result = _denied(
            checks, subject=subject, credential=credential, gate=gate, direction=direction
        )
        result.documents = documents
        result.inside = inside
        return result

    return Verification(
        allowed=True,
        checks=checks,
        subject=subject,
        credential=credential,
        gate=gate,
        direction=direction,
        documents=documents,
        message="All checks passed",
        inside=inside,
    )


def _gate_matches(credential: QrCredential, gate: Gate) -> bool:
    return credential.gate_id is None or credential.gate_id == gate.id


def _verify_employee(
    db: Session, credential: QrCredential, gate: Gate, now: datetime
) -> tuple[Subject | None, list[Check], list[Document]]:
    checks: list[Check] = []
    employee = db.get(Employee, credential.subject_id)
    if employee is None:
        checks.append(
            Check("subject", "Person on file", False, "Employee record missing", DenialReason.UNAUTHORIZED_PERSON)
        )
        return None, checks, []

    subject = Subject(
        type=SubjectType.EMPLOYEE,
        id=employee.id,
        label=employee.full_name,
        reference=employee.employee_code,
        details={
            "department": employee.department,
            "designation": employee.designation,
            "photo_url": employee.photo_url,
            "status": employee.status,
        },
    )
    checks.append(Check("subject", "Person on file", True))

    if employee.status != EmployeeStatus.ACTIVE.value:
        checks.append(
            Check(
                "subject_status",
                "Employee active",
                False,
                f"Employee is {employee.status.lower()}",
                DenialReason.INACTIVE_EMPLOYEE,
            )
        )
        return subject, checks, []
    checks.append(Check("subject_status", "Employee active", True))

    policies = list(
        db.scalars(
            select(AccessPolicy).where(
                AccessPolicy.employee_id == employee.id,
                AccessPolicy.gate_id == gate.id,
                AccessPolicy.is_active.is_(True),
            )
        ).all()
    )
    if not policies:
        checks.append(
            Check(
                "policy_gate",
                "Authorised for this gate",
                False,
                f"No access policy for {gate.name}",
                DenialReason.WRONG_GATE,
            )
        )
        return subject, checks, []
    checks.append(Check("policy_gate", "Authorised for this gate", True))

    today = now.date()
    dated = [p for p in policies if p.valid_from <= today <= p.valid_until]
    if not dated:
        checks.append(
            Check(
                "policy_dates",
                "Policy valid today",
                False,
                "Outside the policy date range",
                DenialReason.NO_ACCESS_POLICY,
            )
        )
        return subject, checks, []
    checks.append(Check("policy_dates", "Policy valid today", True))

    on_day = [p for p in dated if _weekday_allowed(p, now)]
    if not on_day:
        checks.append(
            Check(
                "policy_day",
                "Allowed on this weekday",
                False,
                f"Access not permitted on {now:%A}",
                DenialReason.OUTSIDE_ALLOWED_TIME,
            )
        )
        return subject, checks, []
    checks.append(Check("policy_day", "Allowed on this weekday", True))

    current = now.time()
    in_window = [p for p in on_day if p.start_time <= current <= p.end_time]
    if not in_window:
        window = ", ".join(f"{p.start_time:%H:%M}-{p.end_time:%H:%M}" for p in on_day)
        checks.append(
            Check(
                "policy_time",
                "Within allowed hours",
                False,
                f"Allowed hours: {window}",
                DenialReason.OUTSIDE_ALLOWED_TIME,
            )
        )
        return subject, checks, []
    checks.append(Check("policy_time", "Within allowed hours", True))

    return subject, checks, []


def _verify_visitor(
    db: Session, credential: QrCredential, gate: Gate, now: datetime
) -> tuple[Subject | None, list[Check], list[Document]]:
    checks: list[Check] = []
    visitor = db.get(Visitor, credential.subject_id)
    if visitor is None:
        checks.append(
            Check("subject", "Visit on file", False, "Visitor record missing", DenialReason.UNAUTHORIZED_PERSON)
        )
        return None, checks, []

    subject = Subject(
        type=SubjectType.VISITOR,
        id=visitor.id,
        label=visitor.full_name,
        reference=visitor.reference,
        purpose=visitor.purpose,
        purpose_description=visitor.purpose_description,
        details={
            "company": visitor.company,
            "phone": visitor.phone,
            "host": visitor.host.full_name if visitor.host else None,
            "gate": visitor.gate.name if visitor.gate else None,
            "valid_from": visitor.valid_from,
            "valid_until": visitor.valid_until,
            "status": visitor.status,
        },
    )
    checks.append(Check("subject", "Visit on file", True))

    if visitor.status == VisitorStatus.CANCELLED.value:
        checks.append(
            Check("subject_status", "Visit active", False, "Visit cancelled", DenialReason.REVOKED_QR)
        )
    elif visitor.status in (VisitorStatus.COMPLETED.value, VisitorStatus.EXPIRED.value):
        checks.append(
            Check(
                "subject_status",
                "Visit active",
                False,
                f"Visit {visitor.status.lower()}",
                DenialReason.EXPIRED_VISITOR_PASS,
            )
        )
    else:
        checks.append(Check("subject_status", "Visit active", True))

    checks.append(_gate_check(credential, visitor.gate_id, gate))
    checks.append(
        _window_check(visitor.valid_from, visitor.valid_until, now, DenialReason.EXPIRED_VISITOR_PASS)
    )
    checks.extend(_purpose_checks(db, SubjectType.VISITOR, visitor.id, visitor.purpose, visitor.purpose_description))
    return subject, checks, _documents(db, SubjectType.VISITOR, visitor.id)


def _verify_delivery(
    db: Session, credential: QrCredential, gate: Gate, now: datetime
) -> tuple[Subject | None, list[Check], list[Document]]:
    checks: list[Check] = []
    delivery = db.get(Delivery, credential.subject_id)
    if delivery is None:
        checks.append(
            Check("subject", "Delivery on file", False, "Delivery record missing", DenialReason.UNAUTHORIZED_PERSON)
        )
        return None, checks, []

    subject = Subject(
        type=SubjectType.DELIVERY,
        id=delivery.id,
        label=delivery.driver_name,
        reference=delivery.reference,
        purpose=delivery.purpose,
        purpose_description=delivery.purpose_description,
        details={
            "company": delivery.company,
            "driver_phone": delivery.driver_phone,
            "vehicle_number": delivery.vehicle_number,
            "host_department": delivery.host_department,
            "host": delivery.host.full_name if delivery.host else None,
            "gate": delivery.gate.name if delivery.gate else None,
            "valid_from": delivery.valid_from,
            "valid_until": delivery.valid_until,
            "status": delivery.status,
        },
    )
    checks.append(Check("subject", "Delivery on file", True))

    if delivery.status == DeliveryStatus.CANCELLED.value:
        checks.append(
            Check(
                "subject_status",
                "Delivery active",
                False,
                "Delivery cancelled",
                DenialReason.DELIVERY_CANCELLED,
            )
        )
    elif delivery.status in (DeliveryStatus.COMPLETED.value, DeliveryStatus.EXPIRED.value):
        checks.append(
            Check(
                "subject_status",
                "Delivery active",
                False,
                f"Delivery {delivery.status.lower()}",
                DenialReason.EXPIRED_QR,
            )
        )
    else:
        checks.append(Check("subject_status", "Delivery active", True))

    checks.append(_gate_check(credential, delivery.gate_id, gate))
    checks.append(_window_check(delivery.valid_from, delivery.valid_until, now, DenialReason.EXPIRED_QR))
    checks.extend(
        _purpose_checks(db, SubjectType.DELIVERY, delivery.id, delivery.purpose, delivery.purpose_description)
    )
    return subject, checks, _documents(db, SubjectType.DELIVERY, delivery.id)


def _gate_check(credential: QrCredential, subject_gate_id: int | None, gate: Gate) -> Check:
    authorised = subject_gate_id in (None, gate.id) and _gate_matches(credential, gate)
    return Check(
        "gate",
        "Correct gate",
        authorised,
        None if authorised else f"Pass is not valid at {gate.name}",
        None if authorised else DenialReason.WRONG_GATE,
    )


def _window_check(
    valid_from: datetime, valid_until: datetime, now: datetime, reason: DenialReason
) -> Check:
    if now < valid_from:
        return Check(
            "time_window",
            "Valid time window",
            False,
            f"Pass opens at {valid_from:%d/%m/%Y %H:%M}",
            DenialReason.OUTSIDE_ALLOWED_TIME,
        )
    if now > valid_until:
        return Check(
            "time_window",
            "Valid time window",
            False,
            f"Pass expired at {valid_until:%d/%m/%Y %H:%M}",
            reason,
        )
    return Check("time_window", "Valid time window", True, f"Valid until {valid_until:%H:%M}")


def _purpose_checks(
    db: Session,
    subject_type: SubjectType,
    subject_id: int,
    purpose: str,
    purpose_description: str | None,
) -> list[Check]:
    checks = [Check("purpose", "Purpose recorded", bool(purpose), purpose)]
    if purpose == Purpose.OTHER.value and not purpose_description:
        checks.append(
            Check(
                "purpose_description",
                "Purpose described",
                False,
                "A description is required when the purpose is 'Other'",
                DenialReason.OTHER,
            )
        )
    if Purpose(purpose) in DOCUMENT_REQUIRED_PURPOSES:
        documents = _documents(db, subject_type, subject_id)
        checks.append(
            Check(
                "documents",
                "Supporting document attached",
                bool(documents),
                f"{len(documents)} document(s)" if documents else "No invoice or challan attached",
                None if documents else DenialReason.MISSING_DOCUMENT,
            )
        )
    return checks


def record_decision(
    db: Session,
    *,
    verification: Verification,
    granted: bool,
    guard: User,
    reason: DenialReason | None = None,
    reason_note: str | None = None,
    document_id: int | None = None,
    now: datetime | None = None,
) -> AccessLog:
    """Write the access log and, when granted, move the person in or out."""
    now = now or datetime.utcnow()
    subject = verification.subject
    subject_type = (
        subject.type
        if subject
        else SubjectType(verification.credential.subject_type)
        if verification.credential
        else SubjectType.VISITOR
    )
    log = AccessLog(
        subject_type=subject_type.value,
        subject_id=subject.id if subject else None,
        subject_label=subject.label if subject else "Unknown credential",
        subject_reference=subject.reference if subject else None,
        credential_id=verification.credential.id if verification.credential else None,
        gate_id=verification.gate.id if verification.gate else None,
        direction=verification.direction.value if granted else None,
        status=AccessStatus.GRANTED.value if granted else AccessStatus.DENIED.value,
        reason=reason.value if reason else None,
        reason_note=reason_note,
        purpose=subject.purpose if subject else None,
        document_id=document_id,
        verified_by=guard.id,
        occurred_at=now,
    )
    db.add(log)

    if granted and subject and subject.id is not None:
        if verification.direction is Direction.ENTRY:
            _enter(db, verification, subject, now)
        else:
            _exit(db, verification, subject, subject_type, now)

    db.flush()
    return log


def _enter(db: Session, verification: Verification, subject: Subject, now: datetime) -> None:
    db.add(
        Presence(
            subject_type=subject.type.value,
            subject_id=subject.id,
            subject_label=subject.label,
            subject_reference=subject.reference,
            purpose=subject.purpose,
            host_label=subject.details.get("host"),
            gate_id=verification.gate.id if verification.gate else None,
            entered_at=now,
            expected_exit_at=subject.details.get("valid_until"),
        )
    )
    if subject.type is SubjectType.VISITOR:
        visitor = db.get(Visitor, subject.id)
        if visitor:
            visitor.status = VisitorStatus.INSIDE.value
    elif subject.type is SubjectType.DELIVERY:
        delivery = db.get(Delivery, subject.id)
        if delivery:
            delivery.status = DeliveryStatus.INSIDE.value


def _exit(
    db: Session,
    verification: Verification,
    subject: Subject,
    subject_type: SubjectType,
    now: datetime,
) -> None:
    presence = _presence(db, subject_type, subject.id)
    if presence:
        db.delete(presence)
    if subject.type is SubjectType.VISITOR:
        visitor = db.get(Visitor, subject.id)
        if visitor:
            visitor.status = VisitorStatus.COMPLETED.value
    elif subject.type is SubjectType.DELIVERY:
        delivery = db.get(Delivery, subject.id)
        if delivery:
            delivery.status = DeliveryStatus.COMPLETED.value
        if verification.credential:
            # A delivery pass is single-visit: it dies when the driver leaves.
            verification.credential.status = CredentialStatus.COMPLETED.value
