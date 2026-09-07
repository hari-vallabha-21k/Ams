from datetime import date, timedelta


def test_dashboard_counts(client, world, auth):
    admin = auth("admin@company.com")
    body = client.get("/api/dashboard", headers=admin).json()
    assert body["employees"] == 1
    assert body["active_gates"] == 2
    assert body["currently_inside"] == 0
    assert body["recent_activity"] == []


def test_deactivating_an_employee_revokes_the_credential(client, world, auth):
    admin = auth("admin@company.com")
    guard = auth("guard@company.com")
    response = client.delete(f"/api/employees/{world['employee'].id}", headers=admin)
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"

    verified = client.post(
        "/api/access/verify",
        headers=guard,
        json={"token": world["employee_token"], "gate_id": world["gate"].id},
    ).json()
    assert verified["allowed"] is False


def test_access_policy_crud(client, world, auth):
    admin = auth("admin@company.com")
    created = client.post(
        "/api/access-policies",
        headers=admin,
        json={
            "employee_id": world["employee"].id,
            "gate_id": world["other_gate"].id,
            "valid_from": str(date.today()),
            "valid_until": str(date.today() + timedelta(days=30)),
            "days_of_week": [1, 2, 3, 4, 5],
            "start_time": "09:00:00",
            "end_time": "18:00:00",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["days_of_week"] == [1, 2, 3, 4, 5]

    policy_id = created.json()["id"]
    updated = client.put(
        f"/api/access-policies/{policy_id}", headers=admin, json={"is_active": False}
    )
    assert updated.status_code == 200 and updated.json()["is_active"] is False
    assert client.delete(f"/api/access-policies/{policy_id}", headers=admin).status_code == 204


def test_policy_rejects_an_impossible_window(client, world, auth):
    admin = auth("admin@company.com")
    response = client.post(
        "/api/access-policies",
        headers=admin,
        json={
            "employee_id": world["employee"].id,
            "gate_id": world["gate"].id,
            "valid_from": str(date.today()),
            "valid_until": str(date.today()),
            "days_of_week": [1],
            "start_time": "18:00:00",
            "end_time": "09:00:00",
        },
    )
    assert response.status_code == 422


def test_audit_trail_records_administrative_actions(client, world, auth):
    admin = auth("admin@company.com")
    client.post(
        "/api/gates", headers=admin, json={"code": "G9", "name": "Test Gate"}
    )
    entries = client.get("/api/audit-logs", headers=admin).json()
    actions = [entry["action"] for entry in entries["items"]]
    assert "CREATE_GATE" in actions
    assert "LOGIN" in actions


def test_guard_cannot_read_audit_logs(client, world, auth):
    assert client.get("/api/audit-logs", headers=auth("guard@company.com")).status_code == 403


def test_reports_render_as_csv_and_pdf(client, world, auth):
    admin = auth("admin@company.com")
    csv_response = client.get("/api/reports/deliveries?format=csv", headers=admin)
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "ABC Suppliers" in csv_response.text

    pdf_response = client.get("/api/reports/access?format=pdf", headers=admin)
    assert pdf_response.status_code == 200
    assert pdf_response.content.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_response.content

    gate_report = client.get("/api/reports/gate-wise", headers=admin).json()
    assert gate_report["headers"][0] == "Gate"


def test_documents_reject_unsupported_types(client, world, auth):
    import io

    guard = auth("guard@company.com")
    response = client.post(
        "/api/documents/upload",
        headers=guard,
        data={"subject_type": "DELIVERY", "subject_id": str(world["delivery"].id)},
        files={"file": ("script.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
    )
    assert response.status_code == 415


def test_viewing_a_document_is_audited(client, world, auth):
    import io

    guard = auth("guard@company.com")
    admin = auth("admin@company.com")
    document = client.post(
        "/api/documents/upload",
        headers=guard,
        data={"subject_type": "DELIVERY", "subject_id": str(world["delivery"].id)},
        files={"file": ("invoice.png", io.BytesIO(b"\x89PNG"), "image/png")},
    ).json()
    assert client.get(f"/api/documents/{document['id']}/file", headers=guard).status_code == 200
    entries = client.get("/api/audit-logs?action=VIEW_DOCUMENT", headers=admin).json()
    assert entries["total"] == 1


def test_only_super_admin_manages_users(client, world, auth):
    assert client.get("/api/users", headers=auth("admin@company.com")).status_code == 403
    response = client.post(
        "/api/users",
        headers=auth("root@company.com"),
        json={
            "email": "new.guard@company.com",
            "full_name": "New Guard",
            "role": "SECURITY_GUARD",
            "password": "Password123!",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "SECURITY_GUARD"
