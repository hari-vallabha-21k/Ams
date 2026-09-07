import { useState } from "react";

import PassShare from "../components/PassShare";
import { Alert, Empty, Field, Modal, PageHeader, StatusBadge } from "../components/ui";
import { api } from "../lib/api";
import { WEEKDAYS, formatDateTime, humanise } from "../lib/format";
import { useFetch, useGates } from "../lib/hooks";
import { useAuth } from "../lib/auth";
import type { AccessLog, AccessPolicy, Employee, IssuedCredential, Page } from "../lib/types";

export default function Employees() {
  const { can } = useAuth();
  const [search, setSearch] = useState("");
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  const { data, reload, error } = useFetch<Page<Employee>>(`/api/employees?${query}`, [search]);
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Employee | null>(null);
  const isAdmin = can("ADMIN", "SUPER_ADMIN");

  return (
    <div>
      <PageHeader
        title="Employees"
        subtitle="Employee records, access policies and QR credentials"
        actions={
          isAdmin && (
            <button className="btn-primary" onClick={() => setCreating(true)}>
              Add employee
            </button>
          )
        }
      />

      <input
        className="input mb-3 max-w-xs"
        placeholder="Search name, ID, email or phone"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      {error && <Alert kind="error">{error}</Alert>}

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-100">
            <tr>
              <th className="th">Employee ID</th>
              <th className="th">Name</th>
              <th className="th">Department</th>
              <th className="th">Designation</th>
              <th className="th">Phone</th>
              <th className="th">Status</th>
              <th className="th" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data?.items.map((employee) => (
              <tr key={employee.id}>
                <td className="td font-mono text-xs">{employee.employee_code}</td>
                <td className="td font-medium text-slate-900">{employee.full_name}</td>
                <td className="td">{employee.department}</td>
                <td className="td">{employee.designation}</td>
                <td className="td">{employee.phone}</td>
                <td className="td">
                  <StatusBadge value={employee.status} />
                </td>
                <td className="td text-right">
                  <button className="btn-secondary" onClick={() => setSelected(employee)}>
                    Open
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.items.length === 0 && <Empty message="No employees found." />}
      </div>

      {creating && (
        <EmployeeForm
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            reload();
          }}
        />
      )}
      {selected && (
        <EmployeeDetail
          employee={selected}
          canManage={isAdmin}
          onClose={() => {
            setSelected(null);
            reload();
          }}
        />
      )}
    </div>
  );
}

function EmployeeForm({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({
    employee_code: "",
    full_name: "",
    department: "",
    designation: "",
    phone: "",
    email: "",
    date_joined: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const update = (key: keyof typeof form, value: string) =>
    setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/employees", {
        ...form,
        department: form.department || null,
        designation: form.designation || null,
        phone: form.phone || null,
        email: form.email || null,
        date_joined: form.date_joined || null,
      });
      onCreated();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Add employee" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        {error && <Alert kind="error">{error}</Alert>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Employee ID">
            <input
              className="input"
              required
              value={form.employee_code}
              onChange={(e) => update("employee_code", e.target.value.toUpperCase())}
            />
          </Field>
          <Field label="Full name">
            <input className="input" required value={form.full_name} onChange={(e) => update("full_name", e.target.value)} />
          </Field>
          <Field label="Department">
            <input className="input" value={form.department} onChange={(e) => update("department", e.target.value)} />
          </Field>
          <Field label="Designation">
            <input className="input" value={form.designation} onChange={(e) => update("designation", e.target.value)} />
          </Field>
          <Field label="Phone">
            <input className="input" value={form.phone} onChange={(e) => update("phone", e.target.value)} />
          </Field>
          <Field label="Email">
            <input className="input" type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
          </Field>
          <Field label="Date joined">
            <input className="input" type="date" value={form.date_joined} onChange={(e) => update("date_joined", e.target.value)} />
          </Field>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" disabled={busy}>
            {busy ? "Saving…" : "Save employee"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function EmployeeDetail({
  employee,
  canManage,
  onClose,
}: {
  employee: Employee;
  canManage: boolean;
  onClose: () => void;
}) {
  const gates = useGates();
  const { data: policies, reload: reloadPolicies } = useFetch<AccessPolicy[]>(
    `/api/employees/${employee.id}/policies`,
  );
  const { data: logs } = useFetch<AccessLog[]>(`/api/employees/${employee.id}/access-logs?limit=20`);
  const {
    data: credential,
    reload: reloadCredential,
    error: credentialError,
  } = useFetch<IssuedCredential>(canManage ? `/api/qr/subject/EMPLOYEE/${employee.id}` : null);
  const [adding, setAdding] = useState(false);

  return (
    <Modal title={`${employee.employee_code} · ${employee.full_name}`} onClose={onClose} wide>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Info label="Department" value={employee.department} />
            <Info label="Designation" value={employee.designation} />
            <Info label="Phone" value={employee.phone} />
            <Info label="Email" value={employee.email} />
            <Info label="Status" value={humanise(employee.status)} />
            <Info label="Joined" value={employee.date_joined} />
          </div>

          <div className="rounded-md border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Access policies
              </p>
              {canManage && (
                <button className="text-sm text-brand-600 hover:underline" onClick={() => setAdding(true)}>
                  Add policy
                </button>
              )}
            </div>
            <ul className="divide-y divide-slate-100 text-sm">
              {policies?.map((policy) => (
                <li key={policy.id} className="flex items-start justify-between gap-2 px-3 py-2">
                  <div>
                    <p className="font-medium text-slate-800">
                      {gates.find((gate) => gate.id === policy.gate_id)?.name ?? `Gate ${policy.gate_id}`}
                    </p>
                    <p className="text-xs text-slate-500">
                      {policy.days_of_week
                        .map((day) => WEEKDAYS.find((weekday) => weekday.value === day)?.label)
                        .join(", ")}{" "}
                      · {policy.start_time.slice(0, 5)}–{policy.end_time.slice(0, 5)} ·{" "}
                      {policy.valid_from} → {policy.valid_until}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge value={policy.is_active ? "ACTIVE" : "INACTIVE"} />
                    {canManage && (
                      <button
                        className="text-xs text-rose-600 hover:underline"
                        onClick={async () => {
                          await api.del(`/api/access-policies/${policy.id}`);
                          reloadPolicies();
                        }}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </li>
              ))}
              {policies?.length === 0 && (
                <li className="px-3 py-3 text-slate-400">
                  No policies yet — this employee cannot pass any gate.
                </li>
              )}
            </ul>
          </div>

          <div className="rounded-md border border-slate-200">
            <p className="border-b border-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Recent access history
            </p>
            <ul className="max-h-56 divide-y divide-slate-100 overflow-y-auto text-sm">
              {logs?.map((log) => (
                <li key={log.id} className="flex items-center justify-between px-3 py-2">
                  <span className="text-slate-600">
                    {formatDateTime(log.occurred_at)} · {log.gate_name} · {humanise(log.direction)}
                  </span>
                  <StatusBadge value={log.status} />
                </li>
              ))}
              {logs?.length === 0 && <li className="px-3 py-3 text-slate-400">No access recorded.</li>}
            </ul>
          </div>
        </div>

        <div className="space-y-3">
          {canManage && credentialError && (
            <Alert kind="info">No active QR credential for this employee.</Alert>
          )}
          {canManage && credential && (
            <PassShare
              credential={credential}
              title={`${employee.employee_code} · ${employee.full_name}`}
              message={`Employee pass for ${employee.full_name}.`}
            />
          )}
          {canManage && (
            <div className="grid gap-2 sm:grid-cols-2">
              <button
                className="btn-secondary"
                onClick={async () => {
                  await api.post("/api/qr/generate", {
                    subject_type: "EMPLOYEE",
                    subject_id: employee.id,
                  });
                  reloadCredential();
                }}
              >
                {credential ? "Re-issue QR" : "Issue QR"}
              </button>
              <button
                className="btn-danger"
                disabled={!credential}
                onClick={async () => {
                  await api.post("/api/qr/revoke", {
                    subject_type: "EMPLOYEE",
                    subject_id: employee.id,
                  });
                  reloadCredential();
                }}
              >
                Revoke QR
              </button>
              <button
                className="btn-danger sm:col-span-2"
                disabled={employee.status !== "ACTIVE"}
                onClick={async () => {
                  if (!confirm(`Deactivate ${employee.full_name}?`)) return;
                  await api.del(`/api/employees/${employee.id}`);
                  onClose();
                }}
              >
                Deactivate employee
              </button>
            </div>
          )}
        </div>
      </div>

      {adding && (
        <PolicyForm
          employeeId={employee.id}
          gates={gates}
          onClose={() => setAdding(false)}
          onCreated={() => {
            setAdding(false);
            reloadPolicies();
          }}
        />
      )}
    </Modal>
  );
}

function PolicyForm({
  employeeId,
  gates,
  onClose,
  onCreated,
}: {
  employeeId: number;
  gates: { id: number; name: string }[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const nextYear = new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 10);
  const [form, setForm] = useState({
    gate_id: gates[0]?.id ?? 0,
    valid_from: today,
    valid_until: nextYear,
    start_time: "09:00",
    end_time: "18:00",
  });
  const [days, setDays] = useState<number[]>([1, 2, 3, 4, 5]);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await api.post("/api/access-policies", {
        employee_id: employeeId,
        gate_id: Number(form.gate_id),
        valid_from: form.valid_from,
        valid_until: form.valid_until,
        days_of_week: days,
        start_time: `${form.start_time}:00`,
        end_time: `${form.end_time}:00`,
      });
      onCreated();
    } catch (cause) {
      setError((cause as Error).message);
    }
  };

  return (
    <Modal title="Add access policy" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        {error && <Alert kind="error">{error}</Alert>}
        <Field label="Gate">
          <select
            className="input"
            value={form.gate_id}
            onChange={(e) => setForm({ ...form, gate_id: Number(e.target.value) })}
          >
            {gates.map((gate) => (
              <option key={gate.id} value={gate.id}>
                {gate.name}
              </option>
            ))}
          </select>
        </Field>
        <div>
          <span className="label">Days</span>
          <div className="flex flex-wrap gap-1">
            {WEEKDAYS.map((weekday) => (
              <button
                key={weekday.value}
                type="button"
                className={`btn px-2 py-1 text-xs ${
                  days.includes(weekday.value)
                    ? "bg-brand-600 text-white"
                    : "border border-slate-300 bg-white text-slate-600"
                }`}
                onClick={() =>
                  setDays((current) =>
                    current.includes(weekday.value)
                      ? current.filter((day) => day !== weekday.value)
                      : [...current, weekday.value].sort(),
                  )
                }
              >
                {weekday.label}
              </button>
            ))}
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Valid from">
            <input
              className="input"
              type="date"
              value={form.valid_from}
              onChange={(e) => setForm({ ...form, valid_from: e.target.value })}
            />
          </Field>
          <Field label="Valid until">
            <input
              className="input"
              type="date"
              value={form.valid_until}
              onChange={(e) => setForm({ ...form, valid_until: e.target.value })}
            />
          </Field>
          <Field label="From time">
            <input
              className="input"
              type="time"
              value={form.start_time}
              onChange={(e) => setForm({ ...form, start_time: e.target.value })}
            />
          </Field>
          <Field label="To time">
            <input
              className="input"
              type="time"
              value={form.end_time}
              onChange={(e) => setForm({ ...form, end_time: e.target.value })}
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" disabled={days.length === 0}>
            Save policy
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Info({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="text-slate-800">{value || "—"}</p>
    </div>
  );
}
