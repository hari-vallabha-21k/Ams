# Company Gate Access & Visitor Management System

A web application that controls entry and exit at company gates: employees,
visitors and — as a first-class workflow — deliveries. It issues temporary QR
passes, verifies them at the gate against access policies, records every
decision, and keeps a live list of who is inside.

The guiding principle: **the QR code is never the access decision**. A pass
carries only an opaque token; identity, authorisation, timing, purpose and
paperwork are all resolved server-side by the access engine, which then returns
GRANTED or DENIED with a reason.

- Product requirements: [`docs/PRD.md`](docs/PRD.md)
- Operating procedure: [`docs/PROCESS.md`](docs/PROCESS.md)

## Stack

| Layer     | Choice                                              |
| --------- | --------------------------------------------------- |
| Frontend  | React 18 · TypeScript · Vite · Tailwind CSS          |
| Backend   | FastAPI · SQLAlchemy 2 · Pydantic v2 · JWT           |
| Database  | PostgreSQL (SQLite is used for the test suite)       |
| Documents | Object/file storage on disk, never inside the DB     |
| Delivery  | Docker Compose behind Nginx                          |

## Quick start (Docker)

```bash
cp .env.example .env          # set JWT_SECRET and BOOTSTRAP_PASSWORD
docker compose up --build
```

The app is then on <http://localhost>, the API docs on
<http://localhost/api/docs>. Sign in with `BOOTSTRAP_EMAIL` /
`BOOTSTRAP_PASSWORD` and change the password immediately.

## Quick start (local development)

```bash
# Backend — http://localhost:8000
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL="sqlite:///./gate.db" JWT_SECRET="dev-secret"
python -m app.seed          # demo gates, employees, a delivery and a visitor
uvicorn app.main:app --reload

# Frontend — http://localhost:5173 (proxies /api to the backend)
cd frontend && npm install && npm run dev
```

`python -m app.seed` prints the demo logins and two ready-made pass links.

```bash
cd backend && python -m pytest      # 33 tests: RBAC, access engine, workflows
cd frontend && npm run build        # type-check and bundle
```

## What the system does

**Roles.** Super Admin (users, everything), Admin (people, passes, policies,
reports), Security Guard (the gate: verify, grant, deny, register walk-ins),
Employee (their own pass and history). Every endpoint enforces its own role
check; the UI only hides what the API already refuses.

**Employees.** Records, statuses, access policies per gate (date range,
weekdays, hours) and a re-issuable QR credential. Deactivating an employee
revokes their credential in the same transaction.

**Visitors.** Pre-registered visits with a host, a purpose and a time window,
each with a temporary pass.

**Deliveries.** Reference (`DEL-2026-00001`), company, driver, vehicle, purpose,
host department, gate and validity window; invoices, challans and purchase
orders attached as documents; a pass that can be shared over WhatsApp, copied,
downloaded or printed. The driver opens a link — no account — and shows the QR.

**Gate verification.** The guard picks a gate and direction, scans, and sees
every check the engine ran (credential, status, window, gate, purpose,
documents, presence) before deciding. Denials require a reason, and `OTHER`
requires a note. Nothing is deleted: logs are append-only.

**Occupancy.** Entry and exit maintain a presence table — who is inside, since
when, expected out when — which doubles as the evacuation list.

**Reports.** Access, deliveries, visitors, denied access, gate-wise, entry/exit
and currently-inside, as JSON in the UI or exported to CSV and PDF.

**Audit trail.** Logins, record changes, pass issue and revocation, access
decisions, document views and report exports, with user, entity, IP and
metadata.

## Security

- Passwords hashed with bcrypt; JWT bearer tokens with an expiry.
- QR tokens are 256-bit random and stored **hashed**; a copy encrypted with the
  app secret allows an owner to redisplay their own pass, so a database dump
  alone yields no usable credentials.
- Passes carry no personal data — only the token.
- Verification and pass endpoints are rate limited per client.
- Uploads are restricted by MIME type and size, stored outside the database
  with generated names, and every view is audited.
- The database is never published to the host; secrets come from the
  environment; Nginx terminates the front door (add TLS for production).

## Roadmap beyond this build

Phase 6 (physical hardware: scanner → controller → relay) and the AI features
(invoice OCR, document validation, cross-gate anomaly alerts) are deliberately
out of scope. The access engine already returns a structured decision, so a
gate controller becomes a consumer of `/api/access/grant` rather than a
redesign. Notifications currently surface in the dashboard only; email, SMS and
WhatsApp delivery are future work.

## API surface

`/api/docs` has the full, live reference. The main routes:

```
POST   /api/auth/login            POST   /api/access/verify
GET    /api/employees             POST   /api/access/grant | /entry | /exit | /deny
POST   /api/employees             GET    /api/access/logs
GET    /api/gates                 GET    /api/access/currently-inside
POST   /api/access-policies       GET    /api/access/history/{reference}
GET    /api/visitors              POST   /api/documents/upload
GET    /api/deliveries            GET    /api/documents/{id}/file
POST   /api/deliveries            GET    /api/reports/{report}
POST   /api/qr/generate | /revoke GET    /api/audit-logs
GET    /api/pass/{token}          GET    /api/dashboard
```

## Repository layout

```
backend/    FastAPI service (app/routers, app/services, tests)
frontend/   React application (src/pages, src/components, src/lib)
deploy/     Nginx configuration
docs/       PRD and process document
```

## Schema migrations

Tables are created from the SQLAlchemy models on start-up, which suits a first
deployment. Introduce Alembic before the first schema change in production.
