# Product Requirements Document — Company Gate Access Management System

**Version:** 1.0 · **Product type:** Web-based access and gate management system
**Users:** Super Admin · Admin · Security Guard · Employee · Visitor/Delivery person
**Stack:** React + TypeScript + Tailwind / FastAPI + PostgreSQL / Docker + Nginx

## 1. Product overview

The system digitises and controls entry and exit at company gates. It lets a
company manage employees and visitors, pre-register deliveries, generate
temporary QR passes, verify them at gates, apply access policies, capture the
purpose of a visit, attach supporting documents such as invoices, approve or
deny access, track entry and exit, keep a complete access history, see who is
currently inside, manage multiple gates and generate reports. It is a browser
application.

## 2. Problem statement

Paper registers, phone calls, manual ID checks and informal approvals make it
hard to know who is inside, whether a visitor is authorised, what was
delivered, whether the paperwork is valid, or what was denied and why. Nothing
is centralised and nothing is auditable.

## 3. Goals

Securely control entry and exit; reduce manual work for guards; provide
temporary digital passes; keep complete access logs; support employee, visitor
and delivery workflows; give administrators real-time visibility; support
multiple gates; leave an architecture that can later drive physical gate
hardware.

**Non-goals for the MVP:** facial recognition, fingerprints, RFID, number-plate
recognition, physical gate automation, AI document verification.

## 4. User roles

| Role | Can |
| --- | --- |
| Super Admin | Everything: admins, users, gates, employees, policies, settings, all logs and audit |
| Admin | Employees, visitor and delivery passes, policies, history, documents, dashboard, reports (not Super Admin accounts) |
| Security Guard | Scan and verify passes, register walk-ins, view today's access, record entry and exit, view documents, grant or deny with a reason |
| Employee | Own profile, own QR credential (display, download, print), own access history |
| Visitor / Delivery person | No account: opens a temporary pass link and shows the QR |

## 5. Core modules

Authentication → Dashboard → Employees · Visitors · Deliveries · Gates · Access
policies · QR credentials · Access verification · Documents · Access logs ·
Reports · Audit logs · Notifications.

## 6. Authentication and authorisation

Email and password, hashed passwords, JWT tokens with expiry, logout, and
role-based access control over `SUPER_ADMIN`, `ADMIN`, `SECURITY_GUARD`,
`EMPLOYEE`. Every endpoint enforces its own permissions.

## 7–8. Employees and employee QR

Employee ID, name, photo, department, designation, phone, email, status
(`ACTIVE` / `INACTIVE` / `SUSPENDED`) and joining date. Add, edit, disable,
search, filter, view profile and access history, generate, regenerate or revoke
the QR.

The QR carries **no personal data** — only a random secure token that the
backend resolves to the employee, the credential status, the authorised gates,
the access time and the policy. Credential states: `ACTIVE`, `REVOKED`,
`EXPIRED`.

## 9. Gates

Multiple gates (main entrance, employee entrance, warehouse, parking), each
with a code, name, location, description and `ACTIVE` / `INACTIVE` status.

## 10. Access policies

An access policy binds an employee to a gate with a date range, permitted
weekdays and permitted hours. Verification checks, in order: the person exists,
is active, the credential is valid, the gate is valid, the date is valid, the
time is valid, and a policy permits entry.

## 11. Visitors

Name, company, phone, email, host employee, purpose, gate and a validity
window. The visitor receives a temporary QR.

## 12–15. Deliveries

Delivery ID, company, driver name and phone, vehicle number, purpose, host or
department, gate, validity window and status. A delivery pass is a temporary
credential holding only a random token, tied to the delivery record (not
permanently to the driver), that expires automatically. States: `ACTIVE`,
`USED`, `EXPIRED`, `REVOKED`, `COMPLETED`.

After creating a delivery the system offers **Share via WhatsApp**, **Copy
link**, **Download QR** and **Print pass**. The driver opens a mobile-friendly
pass page showing the QR, delivery ID, company, driver, vehicle, purpose, gate
and validity — with no account.

## 16. Purpose of access

Every visit or delivery records a purpose: material delivery, material pickup,
business meeting, client visit, vendor visit, maintenance, installation,
repair, interview or other. `Other` requires a description.

## 17. Document verification

Invoices, delivery challans, purchase orders and other documents can be
photographed or uploaded as JPG, PNG or PDF. The system stores the document ID,
the access request it belongs to, its type, file name, path, MIME type,
uploader and timestamp. Files live in file/object storage, not in PostgreSQL.

## 18–20. Gate verification

Driver arrives → guard scans → the backend receives token and gate → find the
credential → check its status → check the delivery status → check date and time
→ check the gate → check the purpose → check required documents → show the
result → guard approves or denies → write the access log → grant or deny.

The verification screen shows who is at the gate, the purpose, the paperwork,
each check as pass or fail, a link to view the invoice, and the grant/deny
buttons. A denial requires a reason: invalid, expired or revoked QR, wrong
gate, outside allowed time, unauthorised person, inactive employee, expired
visitor pass, delivery cancelled, missing or invalid document, or other (with a
description).

## 21–22. Entry, exit and logs

Every granted access has a direction, `ENTRY` or `EXIT`, which maintains the
count and list of people currently inside, split by employees, visitors and
delivery personnel. Every attempt — granted or denied — is logged with the
person, gate, credential, timestamp, direction, status, reason, purpose,
verifying user and any document. Logs are never silently deleted.

## 23–26. Dashboard, reports, audit and notifications

The dashboard shows counts (employees, visitors, inside, denied) and recent
activity. Reports cover daily access, employees, visitors, deliveries, denied
access, gate-wise activity, entry/exit and currently-inside, exportable to CSV
and PDF. Administrative actions are audited with user, action, entity, entity
ID, timestamp, IP address and metadata. Notifications in the MVP appear in the
dashboard; email, SMS, WhatsApp and host alerts come later.

## 27–28. Data model and API

Entities: `users`, `employees`, `visitors`, `deliveries`, `gates`,
`access_policies`, `qr_credentials`, `access_requests`, `documents`,
`access_logs`, `audit_logs`. Employees and deliveries each own credentials,
policies and logs; gates own policies and logs; deliveries own documents.

The API covers authentication, employees, gates, visitors, deliveries, QR
generation and revocation, access verification, entry and exit, logs,
currently-inside, document upload and retrieval, and reports.

## 29. Security requirements

HTTPS in production, hashed passwords, JWT authentication, RBAC, input
validation, protection against SQL injection, secure QR tokens with expiry and
revocation, rate limiting on verification endpoints, file type and size
validation, authorised document access, audit logging, a database that is not
publicly exposed, and secrets in environment variables. **Never put sensitive
information inside the QR.**

## 30. Architecture

```
Internet → Nginx → React frontend
                 → FastAPI backend → PostgreSQL
                                   → File storage
                                   → Access engine → gate simulator → future hardware
```

## 31. Phased scope

1. Authentication, RBAC, database, employees, gates, basic dashboard.
2. Employee QR, access policies, scanning, verification, entry/exit, logs.
3. Visitors, deliveries, delivery QR, secure pass link, sharing, purpose,
   document upload.
4. Reports, audit logs, notifications, richer dashboard, search and filtering.
5. Docker, production configuration, Nginx, HTTPS, domain, backups, monitoring.
6. Hardware: scanner → Raspberry Pi/ESP32 → FastAPI → decision → relay → gate.

## 32. Future AI features

Invoice OCR, document validation (missing numbers, expired documents, company
mismatches) and intelligent alerts such as "this delivery has attempted access
at three gates within twenty minutes". Not part of the MVP.

## 33. Success criteria

A guard completes the whole delivery flow — scan, verify, see purpose and
invoice, approve, entry recorded, exit recorded — without administrator help,
and an administrator can later search a reference such as `DEL-2026-00421` and
see the complete history: created, QR generated, QR shared, gate arrival,
invoice, access granted, entry time, exit time and who verified it.

## 34. Product principle

The QR identifies; it does not decide.

```
QR → identification → who are they? what are they doing?
                   → is the credential valid? is the purpose valid?
                   → is the document valid?
                   → ACCESS ENGINE → GRANTED (log it) | DENIED (log the reason)
```

## Implementation status

Phases 1–5 are implemented in this repository. Phase 6 (hardware) and section
32 (AI) are deliberately not; the access engine returns a structured decision
so a gate controller can consume it without redesign. Notifications are limited
to the dashboard, as specified for the MVP.
