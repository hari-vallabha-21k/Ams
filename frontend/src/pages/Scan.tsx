import { useEffect, useRef, useState } from "react";

import { Alert, Field, PageHeader, StatusBadge } from "../components/ui";
import QrScanner from "../components/QrScanner";
import { api, download } from "../lib/api";
import { formatDateTime, humanise } from "../lib/format";
import { useGates, useMeta } from "../lib/hooks";
import type { Direction, Verification } from "../lib/types";

const GATE_KEY = "gate.access.gate";

/** A scanner may return the whole pass URL; only the last segment is the token. */
function extractToken(raw: string): string {
  const value = raw.trim();
  if (!value.includes("/")) return value;
  return value.split("?")[0].split("/").filter(Boolean).pop() ?? value;
}

export default function Scan() {
  const gates = useGates();
  const meta = useMeta();
  const [gateId, setGateId] = useState<number | null>(
    Number(localStorage.getItem(GATE_KEY)) || null,
  );
  const [direction, setDirection] = useState<Direction>("ENTRY");
  const [raw, setRaw] = useState("");
  const [verification, setVerification] = useState<Verification | null>(null);
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [denyReason, setDenyReason] = useState("");
  const [denyNote, setDenyNote] = useState("");
  const [scanning, setScanning] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!gateId && gates.length) setGateId(gates.find((gate) => gate.status === "ACTIVE")?.id ?? gates[0].id);
  }, [gates, gateId]);

  useEffect(() => {
    if (gateId) localStorage.setItem(GATE_KEY, String(gateId));
  }, [gateId]);

  const reset = () => {
    setVerification(null);
    setToken("");
    setRaw("");
    setDenyReason("");
    setDenyNote("");
    inputRef.current?.focus();
  };

  const verify = async (event?: React.FormEvent, overrideRaw?: string) => {
    event?.preventDefault();
    if (!gateId) return;
    const toScan = overrideRaw ?? raw;
    const scanned = extractToken(toScan);
    if (!scanned) return;
    if (overrideRaw) setRaw(overrideRaw);
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await api.post<Verification>("/api/access/verify", {
        token: scanned,
        gate_id: gateId,
        direction,
      });
      setVerification(result);
      setToken(scanned);
      setDenyReason(result.suggested_denial_reason ?? "");
    } catch (cause) {
      setError((cause as Error).message);
      setVerification(null);
    } finally {
      setBusy(false);
    }
  };

  const grant = async () => {
    if (!gateId) return;
    setBusy(true);
    try {
      await api.post("/api/access/grant", { token, gate_id: gateId, direction });
      setNotice(`${direction === "ENTRY" ? "Entry" : "Exit"} recorded for ${verification?.subject?.label}.`);
      reset();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const deny = async () => {
    if (!gateId || !denyReason) return;
    setBusy(true);
    try {
      await api.post("/api/access/deny", {
        token,
        gate_id: gateId,
        direction,
        reason: denyReason,
        reason_note: denyNote || null,
      });
      setNotice(`Access denied and logged (${humanise(denyReason)}).`);
      reset();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Gate verification"
        subtitle="Scan a pass, review what the system found, then grant or deny access"
      />

      <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
        <form onSubmit={verify} className="card space-y-4 p-4">
          <Field label="Gate">
            <select
              className="input"
              value={gateId ?? ""}
              onChange={(event) => setGateId(Number(event.target.value))}
            >
              {gates.map((gate) => (
                <option key={gate.id} value={gate.id} disabled={gate.status !== "ACTIVE"}>
                  {gate.name} {gate.status !== "ACTIVE" ? "(inactive)" : ""}
                </option>
              ))}
            </select>
          </Field>

          <div>
            <span className="label">Direction</span>
            <div className="grid grid-cols-2 gap-2">
              {(["ENTRY", "EXIT"] as Direction[]).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setDirection(value)}
                  className={`btn ${
                    direction === value
                      ? "bg-brand-600 text-white"
                      : "border border-slate-300 bg-white text-slate-600"
                  }`}
                >
                  {humanise(value)}
                </button>
              ))}
            </div>
          </div>

          <Field label="QR token or pass link" hint="Scan with a USB/handheld scanner, paste the link, or use camera.">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                className="input font-mono flex-1"
                autoFocus
                value={raw}
                onChange={(event) => setRaw(event.target.value)}
                placeholder="https://access.company.com/d/…"
              />
              <button
                type="button"
                className="btn-secondary whitespace-nowrap"
                onClick={() => setScanning(!scanning)}
              >
                {scanning ? "Stop camera" : "Use camera"}
              </button>
            </div>
          </Field>

          {scanning && (
            <div className="rounded-md bg-slate-50 p-3">
              <QrScanner
                onScan={(decodedText) => {
                  setScanning(false);
                  verify(undefined, decodedText);
                }}
              />
            </div>
          )}

          <div className="flex gap-2">
            <button className="btn-primary flex-1" disabled={busy || !raw || !gateId}>
              Verify
            </button>
            <button type="button" className="btn-secondary" onClick={reset}>
              Clear
            </button>
          </div>

          {notice && <Alert kind="success">{notice}</Alert>}
          {error && <Alert kind="error">{error}</Alert>}
        </form>

        <div className="card p-4">
          {!verification && (
            <p className="py-16 text-center text-sm text-slate-400">
              Waiting for a scan. The result of every check appears here before you decide.
            </p>
          )}

          {verification && (
            <div className="space-y-4">
              <div
                className={`rounded-md px-4 py-3 text-sm font-semibold ${
                  verification.allowed
                    ? "bg-emerald-50 text-emerald-800"
                    : "bg-rose-50 text-rose-800"
                }`}
              >
                {verification.allowed
                  ? `All checks passed — ready to record ${humanise(direction).toLowerCase()}`
                  : `Blocked: ${verification.message}`}
              </div>

              {verification.subject && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <Detail label="Name" value={verification.subject.label} strong />
                  <Detail label="Reference" value={verification.subject.reference} />
                  <Detail label="Type" value={humanise(verification.subject.type)} />
                  <Detail label="Purpose" value={humanise(verification.subject.purpose)} />
                  {Object.entries(verification.subject.details)
                    .filter(([, value]) => value)
                    .map(([key, value]) => (
                      <Detail
                        key={key}
                        label={humanise(key)}
                        value={
                          key.startsWith("valid_") ? formatDateTime(String(value)) : String(value)
                        }
                      />
                    ))}
                  {verification.subject.purpose_description && (
                    <Detail label="Description" value={verification.subject.purpose_description} />
                  )}
                </div>
              )}

              <div className="rounded-md border border-slate-200">
                <p className="border-b border-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Verification checks
                </p>
                <ul className="divide-y divide-slate-100">
                  {verification.checks.map((check) => (
                    <li key={check.code} className="flex items-start gap-2 px-3 py-2 text-sm">
                      <span className={check.passed ? "text-emerald-600" : "text-rose-600"}>
                        {check.passed ? "✓" : "✕"}
                      </span>
                      <span className="text-slate-700">{check.label}</span>
                      {check.detail && <span className="text-slate-400">— {check.detail}</span>}
                    </li>
                  ))}
                </ul>
              </div>

              {verification.documents.length > 0 && (
                <div className="rounded-md border border-slate-200">
                  <p className="border-b border-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Supporting documents
                  </p>
                  <ul className="divide-y divide-slate-100">
                    {verification.documents.map((document) => (
                      <li key={document.id} className="flex items-center justify-between px-3 py-2 text-sm">
                        <span>
                          {humanise(document.document_type)}
                          {document.reference_number && (
                            <span className="ml-2 text-slate-400">{document.reference_number}</span>
                          )}
                        </span>
                        <button
                          className="btn-secondary"
                          onClick={() =>
                            download(`/api/documents/${document.id}/file`, document.file_name)
                          }
                        >
                          View document
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="no-print grid gap-3 border-t border-slate-200 pt-4 sm:grid-cols-2">
                <button className="btn-success" disabled={!verification.allowed || busy} onClick={grant}>
                  Grant access ({humanise(direction)})
                </button>
                <div className="space-y-2">
                  <select
                    className="input"
                    value={denyReason}
                    onChange={(event) => setDenyReason(event.target.value)}
                  >
                    <option value="">Select a denial reason…</option>
                    {meta?.denial_reasons.map((reason) => (
                      <option key={reason} value={reason}>
                        {humanise(reason)}
                      </option>
                    ))}
                  </select>
                  {denyReason === "OTHER" && (
                    <input
                      className="input"
                      placeholder="Describe the reason"
                      value={denyNote}
                      onChange={(event) => setDenyNote(event.target.value)}
                    />
                  )}
                  <button
                    className="btn-danger w-full"
                    disabled={busy || !denyReason || (denyReason === "OTHER" && !denyNote)}
                    onClick={deny}
                  >
                    Deny access
                  </button>
                </div>
              </div>

              {verification.already_inside && direction === "ENTRY" && (
                <Alert kind="info">
                  This person is already recorded inside. Switch the direction to Exit to record their
                  departure. <StatusBadge value="INSIDE" />
                </Alert>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Detail({
  label,
  value,
  strong,
}: {
  label: string;
  value: string | null | undefined;
  strong?: boolean;
}) {
  if (!value) return null;
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`text-sm ${strong ? "font-semibold text-slate-900" : "text-slate-700"}`}>{value}</p>
    </div>
  );
}
