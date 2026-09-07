import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { request } from "../lib/api";
import { formatDateTime, humanise } from "../lib/format";
import type { PassView } from "../lib/types";

/** The page a driver or visitor opens from their link. No account required. */
export default function PublicPass() {
  const { token } = useParams();
  const [pass, setPass] = useState<PassView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    request<PassView>(`/api/pass/${token}`, { auth: false })
      .then(setPass)
      .catch((cause: Error) => setError(cause.message));
  }, [token]);

  if (error) {
    return (
      <div className="grid min-h-screen place-items-center bg-slate-100 p-6 text-center">
        <div className="card max-w-sm p-6">
          <p className="text-lg font-semibold text-slate-900">Pass unavailable</p>
          <p className="mt-2 text-sm text-slate-500">{error}</p>
        </div>
      </div>
    );
  }

  if (!pass) return <div className="grid min-h-screen place-items-center text-sm text-slate-400">Loading…</div>;

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="card mx-auto max-w-sm overflow-hidden">
        <div className="bg-brand-900 px-5 py-4 text-center text-white">
          <p className="text-xs uppercase tracking-widest text-brand-100">{pass.company_name}</p>
          <p className="text-lg font-semibold">
            {pass.pass_type === "DELIVERY" ? "Delivery Pass" : "Visitor Pass"}
          </p>
        </div>

        <div className="flex flex-col items-center gap-2 px-5 py-6">
          <img src={pass.qr_image} alt="Pass QR code" className="h-56 w-56" />
          <p className="font-mono text-sm text-slate-500">{pass.reference}</p>
        </div>

        <dl className="divide-y divide-slate-100 border-t border-slate-100 px-5 text-sm">
          <Row label={pass.pass_type === "DELIVERY" ? "Driver" : "Visitor"} value={pass.holder_name} />
          <Row label="Company" value={pass.organisation} />
          {pass.vehicle_number && <Row label="Vehicle" value={pass.vehicle_number} />}
          <Row label="Purpose" value={humanise(pass.purpose)} />
          {pass.purpose_description && <Row label="Details" value={pass.purpose_description} />}
          <Row label="Gate" value={pass.gate_name} />
          <Row label="Valid from" value={formatDateTime(pass.valid_from)} />
          <Row label="Valid until" value={formatDateTime(pass.valid_until)} />
          <Row label="Status" value={humanise(pass.status)} />
          {pass.document_count > 0 && (
            <Row label="Documents" value={`${pass.document_count} attached`} />
          )}
        </dl>

        <p className="px-5 py-4 text-center text-xs text-slate-400">
          Show this QR code to security at the gate. Keep this page open on arrival.
        </p>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div className="flex justify-between gap-4 py-2">
      <dt className="text-slate-400">{label}</dt>
      <dd className="text-right font-medium text-slate-800">{value}</dd>
    </div>
  );
}
