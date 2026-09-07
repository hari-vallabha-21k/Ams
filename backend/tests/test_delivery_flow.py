"""The end-to-end workflow the MVP is judged on: create, share, verify, enter, exit."""

import io
from datetime import datetime, timedelta

from app.enums import SubjectType
from app.models import Delivery, Presence


def _iso(offset_hours: float) -> str:
    return (datetime.utcnow() + timedelta(hours=offset_hours)).isoformat()


def test_full_delivery_lifecycle(client, world, auth, db):
    admin = auth("admin@company.com")
    guard = auth("guard@company.com")
    gate_id = world["gate"].id

    # 1. Admin registers the delivery; a pass is issued with it.
    created = client.post(
        "/api/deliveries",
        headers=admin,
        json={
            "company": "ABC Suppliers",
            "driver_name": "Ravi Kumar",
            "driver_phone": "9800000001",
            "vehicle_number": "TS09AB1234",
            "purpose": "MATERIAL_DELIVERY",
            "host_department": "Stores",
            "gate_id": gate_id,
            "valid_from": _iso(-0.5),
            "valid_until": _iso(3),
        },
    )
    assert created.status_code == 201, created.text
    delivery = created.json()
    assert delivery["reference"].startswith("DEL-")

    # 2. The admin fetches the shareable pass (link + QR image).
    issued = client.get(
        f"/api/qr/subject/DELIVERY/{delivery['id']}", headers=admin
    ).json()
    token = issued["token"]
    assert issued["pass_url"].endswith(token)
    assert issued["qr_image"].startswith("data:image/png;base64,")

    # 3. The driver opens the link - no account needed.
    pass_page = client.get(f"/api/pass/{token}")
    assert pass_page.status_code == 200
    assert pass_page.json()["reference"] == delivery["reference"]
    assert pass_page.json()["vehicle_number"] == "TS09AB1234"

    # 4. At the gate the pass fails on the missing invoice.
    verified = client.post(
        "/api/access/verify",
        headers=guard,
        json={"token": token, "gate_id": gate_id, "direction": "ENTRY"},
    ).json()
    assert verified["allowed"] is False
    assert verified["suggested_denial_reason"] == "MISSING_DOCUMENT"

    # 5. The invoice is uploaded and the same pass now passes every check.
    upload = client.post(
        "/api/documents/upload",
        headers=guard,
        data={
            "subject_type": "DELIVERY",
            "subject_id": str(delivery["id"]),
            "document_type": "INVOICE",
            "reference_number": "INV-82731",
        },
        files={"file": ("invoice.pdf", io.BytesIO(b"%PDF-1.4 invoice"), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text

    verified = client.post(
        "/api/access/verify",
        headers=guard,
        json={"token": token, "gate_id": gate_id, "direction": "ENTRY"},
    ).json()
    assert verified["allowed"] is True
    assert verified["subject"]["details"]["vehicle_number"] == "TS09AB1234"
    assert len(verified["documents"]) == 1

    # 6. The guard grants entry.
    entry = client.post(
        "/api/access/entry", headers=guard, json={"token": token, "gate_id": gate_id}
    )
    assert entry.status_code == 200, entry.text
    assert entry.json()["log"]["status"] == "GRANTED"
    assert entry.json()["log"]["direction"] == "ENTRY"

    inside = client.get("/api/access/currently-inside", headers=guard).json()
    assert inside["total"] == 1
    assert inside["delivery"] == 1

    # 7. The driver leaves; the delivery closes and the pass dies with it.
    exit_response = client.post(
        "/api/access/exit", headers=guard, json={"token": token, "gate_id": gate_id}
    )
    assert exit_response.status_code == 200, exit_response.text
    assert exit_response.json()["log"]["direction"] == "EXIT"

    assert db.query(Presence).count() == 0
    db.expire_all()
    assert db.get(Delivery, delivery["id"]).status == "COMPLETED"
    assert client.get(f"/api/pass/{token}").status_code == 404

    # 8. The whole trail is searchable by reference.
    history = client.get(f"/api/access/history/{delivery['reference']}", headers=admin).json()
    assert [log["direction"] for log in history["access_logs"]] == ["ENTRY", "EXIT"]
    actions = {entry["action"] for entry in history["audit_trail"]}
    assert "CREATE_DELIVERY" in actions


def test_denied_access_is_recorded_with_a_reason(client, world, auth):
    guard = auth("guard@company.com")
    admin = auth("admin@company.com")
    gate_id = world["gate"].id
    token = world["delivery_token"]

    denied = client.post(
        "/api/access/deny",
        headers=guard,
        json={
            "token": token,
            "gate_id": gate_id,
            "direction": "ENTRY",
            "reason": "MISSING_DOCUMENT",
            "reason_note": "Driver could not produce the invoice",
        },
    )
    assert denied.status_code == 200, denied.text
    log = denied.json()["log"]
    assert log["status"] == "DENIED"
    assert log["reason"] == "MISSING_DOCUMENT"
    assert log["direction"] is None

    logs = client.get("/api/access/logs?status_filter=DENIED", headers=admin).json()
    assert logs["total"] == 1
    assert logs["items"][0]["reason_note"] == "Driver could not produce the invoice"


def test_grant_is_refused_when_checks_fail(client, world, auth):
    guard = auth("guard@company.com")
    response = client.post(
        "/api/access/grant",
        headers=guard,
        json={"token": world["delivery_token"], "gate_id": world["gate"].id},
    )
    assert response.status_code == 409
    assert "cannot be granted" in response.json()["detail"]


def test_cancelled_delivery_pass_stops_working(client, world, auth, db):
    admin = auth("admin@company.com")
    guard = auth("guard@company.com")
    delivery_id = world["delivery"].id

    assert client.post(f"/api/deliveries/{delivery_id}/revoke", headers=admin).status_code == 200
    verified = client.post(
        "/api/access/verify",
        headers=guard,
        json={"token": world["delivery_token"], "gate_id": world["gate"].id},
    ).json()
    assert verified["allowed"] is False
    assert verified["suggested_denial_reason"] == "REVOKED_QR"
    assert client.get(f"/api/pass/{world['delivery_token']}").status_code == 404


def test_lost_employee_qr_is_replaced(client, world, auth):
    admin = auth("admin@company.com")
    guard = auth("guard@company.com")
    old_token = world["employee_token"]

    issued = client.post(
        "/api/qr/generate",
        headers=admin,
        json={"subject_type": "EMPLOYEE", "subject_id": world["employee"].id},
    )
    assert issued.status_code == 201
    new_token = issued.json()["token"]
    assert new_token != old_token

    old = client.post(
        "/api/access/verify",
        headers=guard,
        json={"token": old_token, "gate_id": world["gate"].id},
    ).json()
    assert old["suggested_denial_reason"] == "REVOKED_QR"

    new = client.post(
        "/api/access/verify",
        headers=guard,
        json={"token": new_token, "gate_id": world["gate"].id},
    ).json()
    assert new["allowed"] is True


def test_employee_sees_own_qr_only(client, world, auth):
    employee = auth("anita@company.com")
    mine = client.get("/api/qr/me", headers=employee)
    assert mine.status_code == 200
    assert mine.json()["credential"]["subject_type"] == SubjectType.EMPLOYEE.value

    other = client.get("/api/qr/subject/DELIVERY/1", headers=employee)
    assert other.status_code == 403
