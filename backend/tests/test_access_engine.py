from datetime import date, datetime, time, timedelta

import pytest

from app.enums import DenialReason, Direction, EmployeeStatus, Role, SubjectType
from app.models import AccessPolicy, Employee, Presence
from app.services import access_engine
from app.services import credentials as credential_service


def checks(result):
    return {c.code: c.passed for c in result.checks}


def test_employee_with_policy_is_allowed(db, world):
    result = access_engine.verify(
        db, token=world["employee_token"], gate_id=world["gate"].id, direction=Direction.ENTRY
    )
    assert result.allowed
    assert result.subject.reference == "EMP1024"
    assert all(checks(result).values())


def test_unknown_token_is_denied(db, world):
    result = access_engine.verify(db, token="not-a-real-token", gate_id=world["gate"].id)
    assert not result.allowed
    assert result.denial_reason is DenialReason.INVALID_QR


def test_employee_denied_at_gate_without_policy(db, world):
    result = access_engine.verify(
        db, token=world["employee_token"], gate_id=world["other_gate"].id
    )
    assert not result.allowed
    assert result.denial_reason is DenialReason.WRONG_GATE


def test_inactive_employee_is_denied(db, world):
    employee = db.get(Employee, world["employee"].id)
    employee.status = EmployeeStatus.SUSPENDED.value
    db.commit()
    result = access_engine.verify(db, token=world["employee_token"], gate_id=world["gate"].id)
    assert not result.allowed
    assert result.denial_reason is DenialReason.INACTIVE_EMPLOYEE


def test_revoked_credential_is_denied(db, world):
    credential_service.revoke_existing(db, SubjectType.EMPLOYEE, world["employee"].id)
    db.commit()
    result = access_engine.verify(db, token=world["employee_token"], gate_id=world["gate"].id)
    assert not result.allowed
    assert result.denial_reason is DenialReason.REVOKED_QR


def test_access_outside_policy_hours_is_denied(db, world):
    db.query(AccessPolicy).filter(AccessPolicy.employee_id == world["employee"].id).update(
        {"start_time": time(9, 0), "end_time": time(9, 30)}
    )
    db.commit()
    moment = datetime.combine(date.today(), time(20, 0))
    result = access_engine.verify(
        db, token=world["employee_token"], gate_id=world["gate"].id, now=moment
    )
    assert not result.allowed
    assert result.denial_reason is DenialReason.OUTSIDE_ALLOWED_TIME


def test_delivery_without_invoice_is_denied(db, world):
    result = access_engine.verify(db, token=world["delivery_token"], gate_id=world["gate"].id)
    assert not result.allowed
    assert result.denial_reason is DenialReason.MISSING_DOCUMENT


def test_expired_delivery_window_is_denied(db, world):
    later = datetime.utcnow() + timedelta(hours=5)
    result = access_engine.verify(
        db, token=world["delivery_token"], gate_id=world["gate"].id, now=later
    )
    assert not result.allowed
    assert result.denial_reason in {DenialReason.EXPIRED_QR, DenialReason.OUTSIDE_ALLOWED_TIME}


def test_visitor_allowed_then_blocked_from_entering_twice(db, world):
    guard = world["users"][Role.SECURITY_GUARD]
    first = access_engine.verify(db, token=world["visitor_token"], gate_id=world["gate"].id)
    assert first.allowed
    access_engine.record_decision(db, verification=first, granted=True, guard=guard)
    db.commit()

    assert db.query(Presence).count() == 1

    second = access_engine.verify(db, token=world["visitor_token"], gate_id=world["gate"].id)
    assert not second.allowed
    assert second.denial_reason is DenialReason.ALREADY_INSIDE


def test_exit_without_entry_is_denied(db, world):
    result = access_engine.verify(
        db, token=world["visitor_token"], gate_id=world["gate"].id, direction=Direction.EXIT
    )
    assert not result.allowed
    assert result.denial_reason is DenialReason.NOT_INSIDE


@pytest.mark.parametrize("direction", [Direction.ENTRY, Direction.EXIT])
def test_inactive_gate_is_denied(db, world, direction):
    world["gate"].status = "INACTIVE"
    db.commit()
    result = access_engine.verify(
        db, token=world["employee_token"], gate_id=world["gate"].id, direction=direction
    )
    assert not result.allowed
    assert result.denial_reason is DenialReason.WRONG_GATE
