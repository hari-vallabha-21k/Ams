def test_login_returns_token_and_profile(client, world):
    response = client.post(
        "/api/auth/login", json={"email": "admin@company.com", "password": "Password123!"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "ADMIN"
    assert body["access_token"]


def test_login_rejects_wrong_password(client, world):
    response = client.post(
        "/api/auth/login", json={"email": "admin@company.com", "password": "nope"}
    )
    assert response.status_code == 401


def test_protected_endpoint_requires_token(client, world):
    assert client.get("/api/employees").status_code == 401


def test_guard_cannot_create_employees(client, world, auth):
    response = client.post(
        "/api/employees",
        headers=auth("guard@company.com"),
        json={"employee_code": "EMP9", "full_name": "New Person"},
    )
    assert response.status_code == 403


def test_employee_cannot_read_another_employee(client, world, auth, db):
    from app.models import Employee

    other = Employee(employee_code="EMP2000", full_name="Someone Else", status="ACTIVE")
    db.add(other)
    db.commit()
    response = client.get(f"/api/employees/{other.id}", headers=auth("anita@company.com"))
    assert response.status_code == 403
    own = client.get(
        f"/api/employees/{world['employee'].id}", headers=auth("anita@company.com")
    )
    assert own.status_code == 200
