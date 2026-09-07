import { useState } from "react";

import PassShare from "../components/PassShare";
import { Alert, Empty, Field, Modal, PageHeader, StatusBadge } from "../components/ui";
import { api } from "../lib/api";
import { formatDateTime, humanise, toIsoUtc, toLocalInput } from "../lib/format";
import { useFetch, useGates, useMeta } from "../lib/hooks";
import type { Employee, IssuedCredential, Page, Visitor } from "../lib/types";

export default function Visitors() {
  const gates = useGates();
  const meta = useMeta();
  const [search, setSearch] = useState("");
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  const { data, reload, error } = useFetch<Page<Visitor>>(`/api/visitors?${query}`, [search]);
  const { data: employees } = useFetch<Page<Employee>>("/api/employees?limit=200");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Visitor | null>(null);

  return (
    <div>
      <PageHeader
        title="Visitors"
        subtitle="Pre-register visits and issue temporary passes"
        actions={
          <button className="btn-primary" onClick={() => setCreating(true)}>
            New visitor pass
          </button>
        }
      />

      <input
        className="input mb-3 max-w-xs"
        placeholder="Search name, company or reference"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      {error && <Alert kind="error">{error}</Alert>}

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-100">
            <tr>
              <th className="th">Reference</th>
              <th className="th">Visitor</th>
              <th className="th">Company</th>
              <th className="th">Host</th>
              <th className="th">Purpose</th>
              <th className="th">Gate</th>
              <th className="th">Valid</th>
              <th className="th">Status</th>
              <th className="th" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data?.items.map((visitor) => (
              <tr key={visitor.id}>
                <td className="td font-mono text-xs">{visitor.reference}</td>
                <td className="td font-medium text-slate-900">{visitor.full_name}</td>
                <td className="td">{visitor.company}</td>
                <td className="td">{visitor.host_name}</td>
                <td className="td">{humanise(visitor.purpose)}</td>
                <td className="td">{visitor.gate_name}</td>
                <td className="td whitespace-nowrap text-xs">
                  {formatDateTime(visitor.valid_from)} → {formatDateTime(visitor.valid_until)}
                </td>
                <td className="td">
                  <StatusBadge value={visitor.status} />
                </td>
                <td className="td text-right">
                  <button className="btn-secondary" onClick={() => setSelected(visitor)}>
                    Pass
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.items.length === 0 && <Empty message="No visitors registered yet." />}
      </div>

      {creating && (
        <VisitorForm
          gates={gates}
          purposes={meta?.purposes ?? []}
          employees={employees?.items ?? []}
          onClose={() => setCreating(false)}
          onCreated={(visitor) => {
            setCreating(false);
            reload();
            setSelected(visitor);
          }}
        />
      )}

      {selected && (
        <VisitorPass
          visitor={selected}
          onClose={() => {
            setSelected(null);
            reload();
          }}
        />
      )}
    </div>
  );
}

function VisitorForm({
  gates,
  purposes,
  employees,
  onClose,
  onCreated,
}: {
  gates: { id: number; name: string; status: string }[];
  purposes: string[];
  employees: Employee[];
  onClose: () => void;
  onCreated: (visitor: Visitor) => void;
}) {
  const now = new Date();
  const [form, setForm] = useState({
    full_name: "",
    company: "",
    phone: "",
    email: "",
    host_employee_id: "",
    purpose: "BUSINESS_MEETING",
    purpose_description: "",
    gate_id: gates[0]?.id ?? 0,
    valid_from: toLocalInput(now),
    valid_until: toLocalInput(new Date(now.getTime() + 4 * 3600 * 1000)),
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const update = (key: keyof typeof form, value: string | number) =>
    setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const visitor = await api.post<Visitor>("/api/visitors", {
        ...form,
        company: form.company || null,
        phone: form.phone || null,
        email: form.email || null,
        purpose_description: form.purpose_description || null,
        host_employee_id: form.host_employee_id ? Number(form.host_employee_id) : null,
        gate_id: Number(form.gate_id),
        valid_from: toIsoUtc(form.valid_from),
        valid_until: toIsoUtc(form.valid_until),
      });
      onCreated(visitor);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Register a visitor" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        {error && <Alert kind="error">{error}</Alert>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Visitor name">
            <input className="input" required value={form.full_name} onChange={(e) => update("full_name", e.target.value)} />
          </Field>
          <Field label="Company">
            <input className="input" value={form.company} onChange={(e) => update("company", e.target.value)} />
          </Field>
          <Field label="Phone">
            <input className="input" value={form.phone} onChange={(e) => update("phone", e.target.value)} />
          </Field>
          <Field label="Email">
            <input className="input" type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
          </Field>
          <Field label="Host employee">
            <select
              className="input"
              value={form.host_employee_id}
              onChange={(e) => update("host_employee_id", e.target.value)}
            >
              <option value="">Not specified</option>
              {employees.map((employee) => (
                <option key={employee.id} value={employee.id}>
                  {employee.full_name} ({employee.employee_code})
                </option>
              ))}
            </select>
          </Field>
          <Field label="Purpose">
            <select className="input" value={form.purpose} onChange={(e) => update("purpose", e.target.value)}>
              {purposes.map((purpose) => (
                <option key={purpose} value={purpose}>
                  {humanise(purpose)}
                </option>
              ))}
            </select>
          </Field>
          {form.purpose === "OTHER" && (
            <div className="sm:col-span-2">
              <Field label="Purpose description">
                <input
                  className="input"
                  required
                  value={form.purpose_description}
                  onChange={(e) => update("purpose_description", e.target.value)}
                />
              </Field>
            </div>
          )}
          <Field label="Gate">
            <select className="input" value={form.gate_id} onChange={(e) => update("gate_id", Number(e.target.value))}>
              {gates.map((gate) => (
                <option key={gate.id} value={gate.id} disabled={gate.status !== "ACTIVE"}>
                  {gate.name}
                </option>
              ))}
            </select>
          </Field>
          <div />
          <Field label="Valid from">
            <input
              className="input"
              type="datetime-local"
              required
              value={form.valid_from}
              onChange={(e) => update("valid_from", e.target.value)}
            />
          </Field>
          <Field label="Valid until">
            <input
              className="input"
              type="datetime-local"
              required
              value={form.valid_until}
              onChange={(e) => update("valid_until", e.target.value)}
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" disabled={busy}>
            {busy ? "Creating…" : "Create and issue pass"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function VisitorPass({ visitor, onClose }: { visitor: Visitor; onClose: () => void }) {
  const { data: credential, error } = useFetch<IssuedCredential>(
    `/api/qr/subject/VISITOR/${visitor.id}`,
  );

  return (
    <Modal title={`${visitor.reference} · ${visitor.full_name}`} onClose={onClose}>
      {error && <Alert kind="info">This visit has no active pass.</Alert>}
      {credential && (
        <div className="space-y-4">
          <PassShare
            credential={credential}
            title={`${visitor.reference} · ${visitor.full_name}`}
            message={`Visitor pass for ${visitor.full_name}. Show this QR at ${visitor.gate_name}.`}
          />
          <button
            className="btn-danger w-full"
            onClick={async () => {
              if (!confirm(`Cancel the visit ${visitor.reference}?`)) return;
              await api.post(`/api/visitors/${visitor.id}/cancel`);
              onClose();
            }}
          >
            Cancel visit and revoke pass
          </button>
        </div>
      )}
    </Modal>
  );
}
