# Process & Operational Workflow — Company Gate Access Management System

**Version:** 1.0 · **Document type:** Business process / SOP

## 1. Purpose

This document defines the standard operating process for managing employees,
visitors, vendors and delivery personnel entering and leaving company premises,
so that only authorised people enter, access follows predefined rules,
deliveries and their paperwork are documented, every movement is recorded, the
guard has a clear approval path, and administrators keep full visibility and
audit history.

## 2. The overall process

```
Access request → registration → credential generated → pass shared
→ person arrives → QR scanned → identity and access verified
→ purpose and documents verified → security decision
    ├── denied  → logged with a reason
    └── approved → entry → person inside → exit → completed → report
```

## 3. Roles and responsibilities

| Role | Responsibility |
| --- | --- |
| Super Admin | System configuration and user administration |
| Admin | Employees, visitors, deliveries and access policies |
| Security Guard | Verify access, manage entry and exit at the gate |
| Employee | Use the assigned QR credential |
| Visitor | Use the temporary visitor QR |
| Delivery person | Use the temporary delivery QR |

## 4. Employee access process

1. **Registration.** The admin creates the employee (ID, name, department,
   designation, phone, email, photo). Status starts `ACTIVE`.
2. **Access policy.** The admin assigns gates, weekdays, hours and a date
   range. Without a policy the employee cannot pass any gate.
3. **QR generation.** The system issues a random credential; the QR contains no
   personal information.
4. **Delivery to the employee.** They open, download or print it from the
   employee portal, or show it on their phone.

## 5. Employee entry

The employee shows the QR; the guard scans it; the system verifies the
credential, employee status, gate, date and time, and returns grant or deny.
Granted access writes an entry log and marks the employee inside. A denial
shows and records the reason: invalid QR, wrong gate, outside allowed time,
inactive employee or expired credential.

## 6. Visitor process

1. **Pre-registration** by an admin or the host: name, company, phone, host,
   purpose, gate, date and time window.
2. **Pass issued** and the secure link shared with the visitor.
3. **Arrival:** scan → verification → guard review → grant or deny.
4. **Entry** recorded; the visitor is marked inside; a physical badge may be
   issued.
5. **Exit** recorded at the gate; the visitor is marked outside.

## 7–10. Delivery registration, documents and sharing

The admin (or security) creates the delivery: reference, company, driver, phone,
vehicle, purpose, gate and validity window. Supporting documents — invoice,
delivery challan, purchase order or other — are attached to the delivery
record. The system then generates a secure token, a temporary QR and a delivery
pass, tied to the delivery rather than permanently to the driver.

The pass is shared by WhatsApp, copied link, downloaded QR or printed pass. The
driver opens the link and shows the QR on their phone; no account is required.

## 11–13. Arrival, verification and the guard's decision

On arrival the guard scans the pass and the screen shows the company, driver,
vehicle, purpose, gate and validity. The system checks automatically:

- **Credential** — does it exist, is it active, expired or revoked?
- **Delivery** — is it still active, or already completed or cancelled?
- **Gate** — is this the authorised gate?
- **Time** — is now inside the allowed window?
- **Documents** — is the required invoice or challan attached?

Each check appears as a tick or a cross with an explanation, alongside a button
to view the document. The guard makes the final decision.

## 14–15. Approval and denial

Approved: the access is granted, an entry log is created and the delivery
person is marked inside. Where no hardware is connected the system simply
displays `ACCESS GRANTED`; later the same decision drives a gate controller and
relay.

Denied: the guard selects a reason — expired QR, wrong gate, outside time,
delivery cancelled, invalid QR, missing invoice, invalid document, unauthorised
vehicle or other — and the denial, its reason, time, gate and verifying guard
become part of the permanent access log.

## 16. Delivery exit

The driver leaves, the QR is scanned, the system identifies the active
delivery, records the exit, marks the person outside and closes the delivery as
`COMPLETED`. The single-visit pass dies with it.

## 17. People currently inside

The system keeps a live list, counted by employees, visitors and delivery
personnel. Selecting a person shows their name, type, entry time, gate,
purpose, host and expected exit.

## 18. Emergency and evacuation

During an emergency, security or an administrator opens the currently-inside
list and exports it as the evacuation list.

## 19–20. Access and audit trails

Every attempt generates an access event with time, person, reference, gate,
purpose and result — including denials and their reasons. Every administrative
action is audited too, so a delivery reads end to end: created, invoice
uploaded, QR generated, QR shared, QR scanned, access granted, exit recorded,
delivery completed.

## 21. Document handling

Upload → validate → store the file → store the metadata → associate with the
access request → security views the document → the view itself is logged.
Allowed formats are PDF, JPG, JPEG and PNG, subject to a maximum size, allowed
MIME types, safe file names and an authorisation check before viewing.

## 22. Exceptions

| Situation | Handling |
| --- | --- |
| Lost QR | Revoke the old credential, generate a new one |
| Delivery cancelled | Delivery → `CANCELLED`, QR → `REVOKED` |
| Wrong vehicle | QR valid but vehicle mismatched → flag for security review |
| Expired delivery | Now past the validity window → denied |
| Missing invoice | Material delivery without a document → denied, or an explicit security override |

## 23. Business rules (enforced in the backend, not only the UI)

1. Inactive employees cannot enter.
2. Expired credentials cannot be used.
3. Revoked credentials cannot be used.
4. Nobody enters through an unauthorised gate.
5. Access outside permitted hours is denied.
6. Every attempt is logged.
7. Delivery passes expire automatically.
8. Cancelled delivery passes cannot be reused.
9. Security cannot modify historical access logs.
10. Only authorised roles view sensitive documents.

## 24. A complete delivery, end to end

| Time | What happens |
| --- | --- |
| 09:00 | The delivery is created for ABC Suppliers — driver Ravi Kumar, vehicle TS09AB1234, material delivery — and the invoice is uploaded |
| 09:01 | A temporary QR is generated and the link is shared over WhatsApp |
| 10:25 | Ravi arrives; the guard scans; every check passes; the guard views the invoice and approves |
| 10:26 | Entry recorded at the main gate against the delivery reference |
| 11:45 | The delivery finishes; the QR is scanned again; exit recorded; the delivery closes as completed |
| Later | An admin searches the reference and reads the whole history |

## 25. The four flows

```
Employee : employee → QR → verify → entry/exit
Visitor  : visitor → request → QR → verify → entry → exit
Delivery : delivery → invoice → QR → share → verify → approve → entry → exit
Admin    : manage → monitor → audit → report
```

## Architecture principle

Keep the business process separate from the UI. The guard's screen may say
**Grant access**, but the backend independently decides whether the credential
is valid, the person authorised, the gate correct, the time valid, the delivery
active and the required documents present. Only then does it produce the access
decision — which is what makes the same system connectable to real gate
hardware later.
