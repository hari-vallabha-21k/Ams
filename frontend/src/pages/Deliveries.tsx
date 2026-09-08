import { useState } from "react";

import PassShare from "../components/PassShare";
import { Alert, Empty, Field, Modal, PageHeader, StatusBadge } from "../components/ui";
import { api } from "../lib/api";
import { formatDateTime, humanise, toIsoUtc, toLocalInput } from "../lib/format";
import { useFetch, useGates, useMeta } from "../lib/hooks";
import type { Delivery, DocumentRecord, IssuedCredential, Page } from "../lib/types";

export default function Deliveries() {
  const gates = useGates();
  const meta = useMeta();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  if (statusFilter) query.set("status_filter", statusFilter);
  const { data, reload, error } = useFetch<Page<Delivery>>(`/api/deliveries?${query}`, [
    search,
    statusFilter,
  ]);

  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Delivery | null>(null);

  return (
    <div>
      <PageHeader
        title="Deliveries"
        subtitle="Pre-register a delivery, attach its paperwork and share the pass with the driver"
        actions={
          <button className="btn-primary" onClick={() => setCreating(true)}>
            New delivery
          </button>
        }
      />

      <div className="mb-3 flex flex-wrap gap-2">
        <input
          className="input max-w-xs"
          placeholder="Search reference, company, driver or vehicle"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select
          className="input max-w-[200px]"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
        >
          <option value="">All statuses</option>
          {["SCHEDULED", "INSIDE", "COMPLETED", "CANCELLED", "EXPIRED"].map((value) => (
            <option key={value} value={value}>
              {humanise(value)}
            </option>
          ))}
        </select>
      </div>

      {error && <Alert kind="error">{error}</Alert>}

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-100">
            <tr>
              <th className="th">Reference</th>
              <th className="th">Company</th>
              <th className="th">Driver</th>
              <th className="th">Vehicle</th>
              <th className="th">Gate</th>
              <th className="th">Valid</th>
              <th className="th">Status</th>
              <th className="th" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data?.items.map((delivery) => (
              <tr key={delivery.id}>
                <td className="td font-mono text-xs">{delivery.reference}</td>
                <td className="td font-medium text-slate-900">{delivery.company}</td>
                <td className="td">{delivery.driver_name}</td>
                <td className="td">{delivery.vehicle_number}</td>
                <td className="td">{delivery.gate_name}</td>
                <td className="td whitespace-nowrap text-xs">
                  {formatDateTime(delivery.valid_from)} → {formatDateTime(delivery.valid_until)}
                </td>
                <td className="td">
                  <StatusBadge value={delivery.status} />
                </td>
                <td className="td text-right">
                  <button className="btn-secondary" onClick={() => setSelected(delivery)}>
                    Manage
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.items.length === 0 && <Empty message="No deliveries match this filter." />}
      </div>

      {creating && (
        <DeliveryForm
          gates={gates}
          purposes={meta?.purposes ?? []}
          onClose={() => setCreating(false)}
          onCreated={(delivery) => {
            setCreating(false);
            reload();
            setSelected(delivery);
          }}
        />
      )}

      {selected && (
        <DeliveryDetail
          delivery={selected}
          documentTypes={meta?.document_types ?? []}
          onClose={() => {
            setSelected(null);
            reload();
          }}
        />
      )}
    </div>
  );
}

function DeliveryForm({
  gates,
  purposes,
  onClose,
  onCreated,
}: {
  gates: { id: number; name: string; status: string }[];
  purposes: string[];
  onClose: () => void;
  onCreated: (delivery: Delivery) => void;
}) {
  const now = new Date();
  const [form, setForm] = useState({
    company: "",
    driver_name: "",
    driver_phone: "",
    vehicle_number: "",
    purpose: "MATERIAL_DELIVERY",
    purpose_description: "",
    host_department: "",
    gate_id: gates[0]?.id ?? 0,
    valid_from: toLocalInput(now),
    valid_until: toLocalInput(new Date(now.getTime() + 3 * 3600 * 1000)),
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
      const delivery = await api.post<Delivery>("/api/deliveries", {
        ...form,
        driver_phone: form.driver_phone || null,
        vehicle_number: form.vehicle_number || null,
        host_department: form.host_department || null,
        purpose_description: form.purpose_description || null,
        gate_id: Number(form.gate_id),
        valid_from: toIsoUtc(form.valid_from),
        valid_until: toIsoUtc(form.valid_until),
      });
      onCreated(delivery);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Register a delivery" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        {error && <Alert kind="error">{error}</Alert>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Supplier company">
            <input className="input" required value={form.company} onChange={(e) => update("company", e.target.value)} />
          </Field>
          <Field label="Driver name">
            <input
              className="input"
              required
              value={form.driver_name}
              onChange={(e) => update("driver_name", e.target.value)}
            />
          </Field>
          <Field label="Driver phone">
            <input className="input" value={form.driver_phone} onChange={(e) => update("driver_phone", e.target.value)} />
          </Field>
          <Field label="Vehicle number">
            <input
              className="input"
              value={form.vehicle_number}
              onChange={(e) => update("vehicle_number", e.target.value.toUpperCase())}
            />
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
          <Field label="Host department">
            <input
              className="input"
              value={form.host_department}
              onChange={(e) => update("host_department", e.target.value)}
            />
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

function DeliveryDetail({
  delivery,
  documentTypes,
  onClose,
}: {
  delivery: Delivery;
  documentTypes: string[];
  onClose: () => void;
}) {
  const { data: credential, reload: reloadCredential, error: credentialError } =
    useFetch<IssuedCredential>(`/api/qr/subject/DELIVERY/${delivery.id}`);
  const { data: documents, reload: reloadDocuments } = useFetch<DocumentRecord[]>(
    `/api/deliveries/${delivery.id}/documents`,
  );
  const [documentType, setDocumentType] = useState("INVOICE");
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const upload = async (file: File) => {
    setBusy(true);
    setError(null);
    const formData = new FormData();
    formData.append("subject_type", "DELIVERY");
    formData.append("subject_id", String(delivery.id));
    formData.append("document_type", documentType);
    if (reference) formData.append("reference_number", reference);
    formData.append("file", file);
    try {
      await api.upload("/api/documents/upload", formData);
      setReference("");
      reloadDocuments();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!confirm(`Cancel ${delivery.reference}? The pass stops working immediately.`)) return;
    await api.post(`/api/deliveries/${delivery.id}/revoke`);
    onClose();
  };

  return (
    <Modal title={`${delivery.reference} · ${delivery.company}`} onClose={onClose} wide>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Info label="Driver" value={delivery.driver_name} />
            <Info label="Phone" value={delivery.driver_phone} />
            <Info label="Vehicle" value={delivery.vehicle_number} />
            <Info label="Purpose" value={humanise(delivery.purpose)} />
            <Info label="Gate" value={delivery.gate_name} />
            <Info label="Status" value={humanise(delivery.status)} />
            <Info label="Valid from" value={formatDateTime(delivery.valid_from)} />
            <Info label="Valid until" value={formatDateTime(delivery.valid_until)} />
          </div>

          <div className="rounded-md border border-slate-200 p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Supporting documents
            </p>
            <ul className="mb-3 divide-y divide-slate-100 text-sm">
              {documents?.map((document) => (
                <li key={document.id} className="py-1.5">
                  {humanise(document.document_type)}
                  {document.reference_number && (
                    <span className="ml-2 text-slate-400">{document.reference_number}</span>
                  )}
                  <span className="ml-2 text-xs text-slate-400">{document.file_name}</span>
                </li>
              ))}
              {documents?.length === 0 && (
                <li className="py-2 text-slate-400">
                  No documents yet. Material deliveries need an invoice or challan before entry.
                </li>
              )}
            </ul>
            {error && <Alert kind="error">{error}</Alert>}
            <div className="grid gap-2 sm:grid-cols-2">
              <select className="input" value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
                {documentTypes.map((type) => (
                  <option key={type} value={type}>
                    {humanise(type)}
                  </option>
                ))}
              </select>
              <input
                className="input"
                placeholder="Document number"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
              />
            </div>
            <div className="mt-3 flex gap-2">
              <label className="btn-secondary flex-1 cursor-pointer text-center">
                <span>Upload soft copy</span>
                <input
                  type="file"
                  className="hidden"
                  accept="application/pdf,image/png,image/jpeg"
                  disabled={busy}
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) upload(file);
                    event.target.value = "";
                  }}
                />
              </label>
              <label className="btn-secondary flex-1 cursor-pointer text-center">
                <span>Scan hardcopy</span>
                <input
                  type="file"
                  className="hidden"
                  accept="image/*"
                  capture="environment"
                  disabled={busy}
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) upload(file);
                    event.target.value = "";
                  }}
                />
              </label>
            </div>
          </div>

          <button className="btn-danger" onClick={cancel} disabled={delivery.status === "CANCELLED"}>
            Cancel delivery and revoke pass
          </button>
        </div>

        <div>
          {credentialError && (
            <div className="space-y-2">
              <Alert kind="info">This delivery has no active pass.</Alert>
              <button
                className="btn-primary"
                onClick={async () => {
                  await api.post("/api/qr/generate", {
                    subject_type: "DELIVERY",
                    subject_id: delivery.id,
                  });
                  reloadCredential();
                }}
              >
                Issue a new pass
              </button>
            </div>
          )}
          {credential && (
            <PassShare
              credential={credential}
              title={`${delivery.reference} · ${delivery.driver_name}`}
              message={`Delivery pass for ${delivery.company} (${delivery.reference}). Show this QR at ${delivery.gate_name}.`}
            />
          )}
        </div>
      </div>
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
