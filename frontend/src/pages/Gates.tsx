import { useState } from "react";

import { Alert, Empty, Field, Modal, PageHeader, StatusBadge } from "../components/ui";
import { api } from "../lib/api";
import { useFetch } from "../lib/hooks";
import type { Gate } from "../lib/types";

export default function Gates() {
  const { data, reload, error } = useFetch<Gate[]>("/api/gates");
  const [creating, setCreating] = useState(false);

  const toggle = async (gate: Gate) => {
    await api.put(`/api/gates/${gate.id}`, {
      status: gate.status === "ACTIVE" ? "INACTIVE" : "ACTIVE",
    });
    reload();
  };

  return (
    <div>
      <PageHeader
        title="Gates"
        subtitle="Every entry point the system controls"
        actions={
          <button className="btn-primary" onClick={() => setCreating(true)}>
            Add gate
          </button>
        }
      />
      {error && <Alert kind="error">{error}</Alert>}

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-100">
            <tr>
              <th className="th">Code</th>
              <th className="th">Name</th>
              <th className="th">Location</th>
              <th className="th">Description</th>
              <th className="th">Status</th>
              <th className="th" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data?.map((gate) => (
              <tr key={gate.id}>
                <td className="td font-mono text-xs">{gate.code}</td>
                <td className="td font-medium text-slate-900">{gate.name}</td>
                <td className="td">{gate.location}</td>
                <td className="td">{gate.description}</td>
                <td className="td">
                  <StatusBadge value={gate.status} />
                </td>
                <td className="td text-right">
                  <button className="btn-secondary" onClick={() => toggle(gate)}>
                    {gate.status === "ACTIVE" ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.length === 0 && <Empty message="No gates configured yet." />}
      </div>

      {creating && (
        <GateForm
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            reload();
          }}
        />
      )}
    </div>
  );
}

function GateForm({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ code: "", name: "", location: "", description: "" });
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await api.post("/api/gates", {
        ...form,
        location: form.location || null,
        description: form.description || null,
      });
      onCreated();
    } catch (cause) {
      setError((cause as Error).message);
    }
  };

  return (
    <Modal title="Add gate" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        {error && <Alert kind="error">{error}</Alert>}
        <Field label="Gate code">
          <input
            className="input"
            required
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
          />
        </Field>
        <Field label="Name">
          <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Location">
          <input className="input" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
        </Field>
        <Field label="Description">
          <textarea
            className="input"
            rows={2}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </Field>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary">Save gate</button>
        </div>
      </form>
    </Modal>
  );
}
