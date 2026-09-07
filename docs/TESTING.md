# Manual Test Plan

How to test the Gate Access Management System by hand, end to end. Work top to
bottom: each section assumes the data created by the ones before it.

The automated suite (`cd backend && python -m pytest`, 33 tests) already covers
the access engine's decision logic, RBAC and the delivery lifecycle at the API
level. Manual testing is for what it cannot see: the screens, the timing, the
sharing, the printing, and the awkward things real people do at a gate.

---

## 0. Set up the test environment

Use a throwaway database — several tests deactivate people and cancel passes.

```bash
# Terminal 1 — backend on :8000
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL="sqlite:///./manual-test.db"
export JWT_SECRET="test-secret"
export PUBLIC_BASE_URL="http://localhost:5173"
python -m app.seed            # note the printed logins and two pass links
uvicorn app.main:app --reload

# Terminal 2 — web app on :5173
cd frontend && npm install && npm run dev
```

Open <http://localhost:5173>. To start over: stop both, `rm backend/manual-test.db`,
re-seed.

### Accounts

| Role | Email | Password |
| --- | --- | --- |
| Super Admin | `admin@company.com` | `ChangeMe123!` (bootstrap) |
| Admin | `admin.desk@company.com` | `Password123!` |
| Security Guard | `guard@company.com` | `Password123!` |
| Employee | `anita.rao@company.com` | `Password123!` |

### Seeded data

Four gates (Main Entrance, Employee Entrance, Warehouse, Parking — Parking is
`INACTIVE`), three employees (EMP1024 and EMP1025 active with policies on the
first two gates, EMP1026 inactive), one delivery `DEL-2026-00001` with an
invoice, and one visitor `VIS-2026-00001`. The seed prints a delivery pass link
and a visitor pass link — keep that terminal output; you will paste those
tokens into the gate screen.

### Two habits that make this go faster

- **Getting a token to "scan":** open the record, press **Copy link**, and
  paste the whole URL into the gate screen's token box. It accepts a full pass
  URL or a bare token.
- **Testing time windows without waiting:** create a pass with a validity
  window that has already closed (set *Valid until* to an hour ago) or is not
  yet open (set *Valid from* to an hour ahead). That is how you force the
  timing denials in section 8.

---

## 1. Smoke test (2 minutes)

| # | Step | Expected |
| --- | --- | --- |
| 1.1 | `curl http://localhost:8000/api/health` | `{"status":"ok",...}` |
| 1.2 | Open <http://localhost:5173> signed out | Redirected to the login screen |
| 1.3 | Sign in as the admin | Dashboard with five stat cards |
| 1.4 | Open <http://localhost:8000/api/docs> | Interactive API reference loads |

If any of these fail, stop and fix the environment before going further.

---

## 2. Authentication

| # | Step | Expected |
| --- | --- | --- |
| 2.1 | Log in with a wrong password | "Invalid email or password"; no session |
| 2.2 | Log in with an unknown email | Same message (it must not reveal whether the account exists) |
| 2.3 | Log in as the admin | Lands on the dashboard, name shown top right |
| 2.4 | Reload the page | Still signed in |
| 2.5 | Sign out, then press the browser Back button | Bounced back to login, no data visible |
| 2.6 | With DevTools, delete the `gate.access.token` key and reload | Returned to login |

---

## 3. Role permissions

Sign in as each role and confirm the navigation and the refusals. The UI hides
what a role cannot use, but the API is the real guard — case 3.5 checks that.

| # | Role | Expected |
| --- | --- | --- |
| 3.1 | Super Admin | All sections; can create users via the API (`POST /api/users`) |
| 3.2 | Admin | Everything except user administration |
| 3.3 | Security Guard | Dashboard, gate verification, currently inside, deliveries, visitors, employees, access logs, my pass — **no** Gates, Reports or Audit trail |
| 3.4 | Employee | Only "My pass"; visiting `/employees` or `/reports` directly redirects back |
| 3.5 | Guard, in DevTools console: `fetch('/api/audit-logs',{headers:{Authorization:'Bearer '+localStorage['gate.access.token']}}).then(r=>console.log(r.status))` | `403` — the server refuses even though the link is hidden |
| 3.6 | Employee: open another employee's record by URL/API | `403` |

---

## 4. Gates

| # | Step | Expected |
| --- | --- | --- |
| 4.1 | Gates → Add gate: code `G5`, name `Test Gate` | Appears in the list as Active |
| 4.2 | Add another gate with code `G5` | Rejected: "Gate code already exists" |
| 4.3 | Deactivate `G5` | Status becomes Inactive |
| 4.4 | Open gate verification | `G5` and Parking appear disabled in the gate picker |
| 4.5 | Verify any valid pass against an inactive gate (pick it via the API if the UI blocks you) | Denied, reason wrong gate |

---

## 5. Employees, policies and credentials

| # | Step | Expected |
| --- | --- | --- |
| 5.1 | Employees → Add employee `EMP2001 / Test Person` | Created, status Active |
| 5.2 | Add another with the same ID | Rejected: "Employee ID already exists" |
| 5.3 | Search "2001", then "test" | Both find the record |
| 5.4 | Open EMP2001 → Issue QR | QR image, pass link and the four share buttons appear |
| 5.5 | Add a policy: Main Entrance, Mon–Sun, 00:00–23:59, today → next year | Listed as Active |
| 5.6 | Try a policy with end time before start time | Rejected (validation error) |
| 5.7 | Re-issue the QR | A **different** link; the old token must fail at the gate (case 8.3) |
| 5.8 | Revoke the QR, then re-issue it | Revoke succeeds; the panel shows a fresh pass |
| 5.9 | Deactivate EMP2001 | Status Inactive **and** the credential is revoked automatically |
| 5.10 | Check the list again | The employee is still there — records are never deleted |

---

## 6. Employee entry and exit

Use EMP1024 (Anita Rao); copy her pass link from her employee record.

| # | Step | Expected |
| --- | --- | --- |
| 6.1 | Gate verification → Main Entrance, Entry, paste the link, Verify | All checks green: credential, window, employee active, gate authorised, policy dates, weekday, hours |
| 6.2 | Grant access | Confirmation message; the form clears ready for the next person |
| 6.3 | Currently inside | Total 1, Employees 1, with her entry time and gate |
| 6.4 | Verify the same pass again as Entry | Denied: already recorded inside |
| 6.5 | Switch to Exit and verify | All green |
| 6.6 | Grant | Currently inside returns to 0 |
| 6.7 | Verify as Exit again | Denied: no open entry found |
| 6.8 | Employees → EMP1024 → Recent access history | Both the entry and the exit are listed |

---

## 7. Visitors

| # | Step | Expected |
| --- | --- | --- |
| 7.1 | Visitors → New visitor pass, host = Anita Rao, purpose Business Meeting, window "now → +4h" | Created with a `VIS-…` reference and a pass |
| 7.2 | Create one with purpose **Other** and no description | Rejected until you type a description |
| 7.3 | Open the pass → Copy link → open it in a private window | Visitor pass page renders with no login |
| 7.4 | Verify and grant entry at the gate | Visitor status becomes Inside; occupancy counts them |
| 7.5 | Grant exit | Status Completed |
| 7.6 | Create a second visitor, then Cancel visit | Status Cancelled; the pass link now shows "Pass unavailable"; verification denies it |

---

## 8. Deliveries — the main workflow

This is the flow the MVP is judged on. Run it exactly as a working day would.

| # | Step | Expected |
| --- | --- | --- |
| 8.1 | Deliveries → New delivery: ABC Suppliers, driver Ravi Kumar, vehicle TS09AB1234, Material Delivery, Main Entrance, now → +3h | Created with a `DEL-<year>-<nnnnn>` reference |
| 8.2 | Open it → the pass panel shows a QR, link and Share/Copy/Download/Print | Download saves a PNG; Print opens a print dialog showing the pass without the navigation |
| 8.3 | Share on WhatsApp | Opens `wa.me` with the message and link pre-filled |
| 8.4 | Open the link on a phone (or a narrow window) | Mobile-friendly pass: QR, reference, driver, company, vehicle, purpose, gate, validity |
| 8.5 | At the gate, verify it as Entry **before** uploading any document | **Denied** — "Supporting document attached" fails, suggested reason Missing document |
| 8.6 | Upload an invoice (PDF or photo) with number `INV-82731` | Listed under supporting documents |
| 8.7 | Verify again | All checks green; the document is listed with a **View document** button |
| 8.8 | Press View document | The invoice opens/downloads |
| 8.9 | Grant entry | Log recorded; delivery status Inside; occupancy +1 |
| 8.10 | Grant exit | Delivery status Completed; occupancy back to 0 |
| 8.11 | Open the driver's pass link again | "Pass unavailable" — a delivery pass is single-visit |
| 8.12 | Verify the same token again | Denied (credential completed/expired) |

---

## 9. Every denial reason

Force each one and confirm the screen explains it and the log records it. This
is the section most worth doing carefully — it is what a guard will actually
hit.

| # | How to force it | Expected reason |
| --- | --- | --- |
| 9.1 | Type nonsense into the token box | Invalid QR |
| 9.2 | Present a pass whose *Valid until* is in the past | Expired QR |
| 9.3 | Revoke a credential, then present it | Revoked QR |
| 9.4 | Present a Main Entrance pass at the Warehouse gate | Wrong gate |
| 9.5 | Present a pass whose *Valid from* is an hour ahead | Outside allowed time |
| 9.6 | Employee pass at a gate with no policy (e.g. Warehouse) | Wrong gate / no access policy |
| 9.7 | Give an employee a policy of 09:00–09:30 and scan outside it | Outside allowed time |
| 9.8 | Deactivate an employee and scan their old pass | Inactive employee |
| 9.9 | Cancel a delivery and scan its pass | Delivery cancelled / revoked |
| 9.10 | Material delivery with no document | Missing document |
| 9.11 | Scan someone already inside as Entry | Already inside |
| 9.12 | Scan someone not inside as Exit | Not inside |

Then, on any failing verification:

| # | Step | Expected |
| --- | --- | --- |
| 9.13 | Press **Grant access** | Impossible — the button is disabled; the API also refuses (409) |
| 9.14 | Choose a denial reason and deny | Recorded; the message names the reason |
| 9.15 | Choose reason **Other** and leave the note empty | Deny stays disabled until you describe it |
| 9.16 | Access logs | The denial appears with reason and note, and **no** direction |

---

## 10. Occupancy and evacuation

| # | Step | Expected |
| --- | --- | --- |
| 10.1 | Grant entry to one employee, one visitor and one delivery | Currently inside: total 3, split 1/1/1 |
| 10.2 | Read the table | Each row shows reference, purpose, host, gate, entry time, expected exit |
| 10.3 | Export evacuation list (admin) | A PDF downloads listing exactly those people |
| 10.4 | Grant exit to one of them, refresh | Total drops to 2 and that person disappears |

---

## 11. Access logs and history

| # | Step | Expected |
| --- | --- | --- |
| 11.1 | Access logs — filter by type, result, direction and gate | Each filter narrows the list correctly |
| 11.2 | Search a delivery reference | Only that delivery's events |
| 11.3 | Check any row | Time, person, gate, direction, result, reason and the verifying guard's name |
| 11.4 | `GET /api/access/history/DEL-2026-00001` (or search the reference) | Full trail: created, invoice uploaded, QR generated, entry, exit, completed |
| 11.5 | Try to delete or edit a log | No such control exists in the UI or API |

---

## 12. Reports

For each of the seven reports — daily access, deliveries, visitors, denied
access, gate-wise, entry/exit, currently inside:

| # | Step | Expected |
| --- | --- | --- |
| 12.1 | Select it and set a date range covering today | The table matches what you did above |
| 12.2 | Set a range in the past with no activity | Empty state, not an error |
| 12.3 | Export CSV | Opens in a spreadsheet with the same rows and a header line |
| 12.4 | Export PDF | Opens in a PDF reader, readable, paginated, with the title and generation time |
| 12.5 | Entry/exit report | Paired entries and exits with time on site; people still inside show "still inside" |

---

## 13. Audit trail

| # | Step | Expected |
| --- | --- | --- |
| 13.1 | Audit trail after the sections above | Logins, employee/gate/delivery/visitor creation, QR generation and revocation, grants, denials, document uploads and views, report exports |
| 13.2 | Filter by action `VIEW_DOCUMENT` | Only document views — confirming that reading an invoice is itself recorded |
| 13.3 | Check a row | User, action, entity, entity ID, IP address, timestamp and metadata |
| 13.4 | Sign in as the guard and look for the section | Not available (403) |

---

## 14. Documents

| # | Step | Expected |
| --- | --- | --- |
| 14.1 | Upload a PDF, a JPG and a PNG | All accepted |
| 14.2 | Upload a `.exe` or `.docx` | Rejected: unsupported file type |
| 14.3 | Upload a file larger than 10 MB | Rejected: size limit |
| 14.4 | Upload a file named `../../etc/passwd.pdf` | Accepted but stored under a generated name; nothing escapes the storage directory |
| 14.5 | Request a document URL while signed out | 401, not the file |

---

## 15. Security spot-checks

| # | Step | Expected |
| --- | --- | --- |
| 15.1 | Decode a pass QR with any phone scanner | Only a URL with a random token — no name, phone or company |
| 15.2 | Change one character of a pass token in the URL | "Pass unavailable" |
| 15.3 | Call `/api/access/verify` more than 60 times in a minute | `429 Too many verification attempts` |
| 15.4 | Call any admin endpoint with no `Authorization` header | 401 |
| 15.5 | Inspect `qr_credentials` in the database | `token_hash` and `token_encrypted` only — no plaintext token |
| 15.6 | Try a login of `admin.desk@company.com' OR '1'='1` | Ordinary failed login, no error leak |

---

## 16. Browsers, devices and printing

| # | Step | Expected |
| --- | --- | --- |
| 16.1 | Chrome, Firefox and Safari (or Edge) | Same behaviour throughout |
| 16.2 | Pass page on a real phone | Readable without zooming; QR scannable from the screen |
| 16.3 | Gate verification on a tablet | Usable one-handed; the token field keeps focus for a handheld scanner |
| 16.4 | Print a pass (Ctrl/Cmd-P) | Only the pass prints — no navigation or buttons |
| 16.5 | A physical USB/Bluetooth QR scanner, if you have one | Scanning fills the token box and submits like typed input |

---

## 17. Deployment check

Run once against the Docker stack before handing it to anyone:

| # | Step | Expected |
| --- | --- | --- |
| 17.1 | `cp .env.example .env`, set `JWT_SECRET` and `BOOTSTRAP_PASSWORD`, `docker compose up --build` | All three containers healthy |
| 17.2 | Open `http://localhost` and sign in with the bootstrap account | Dashboard loads through Nginx |
| 17.3 | Change the bootstrap password immediately | Old password no longer works |
| 17.4 | Repeat sections 6 and 8 against this deployment | Identical behaviour |
| 17.5 | `docker compose restart backend` | Data survives; occupancy and logs unchanged |
| 17.6 | Try to reach PostgreSQL from the host (`psql -h localhost -p 5432`) | Refused — the database is not published |

---

## Recording results

Track each case as Pass / Fail / Blocked with the date and who ran it. For a
failure, capture:

```
Case:        8.5
Environment: local dev / docker, browser + version
Role:        Security Guard
Steps:       what you did, in order
Expected:    what the plan says
Actual:      what happened (with a screenshot)
Severity:    blocker / major / minor / cosmetic
```

**Blocker** means a person is wrongly let in or wrongly turned away, or an
access event is not recorded — treat anything in sections 6, 8 and 9 that way.

## Known gaps this plan does not cover

Physical gate hardware, invoice OCR and document validation, and email/SMS/
WhatsApp notifications are not built (see the PRD's phase 6 and section 32).
Notifications exist only as dashboard information today.
