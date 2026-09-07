import PassShare from "../components/PassShare";
import { Alert, PageHeader } from "../components/ui";
import { formatDateTime } from "../lib/format";
import { useAuth } from "../lib/auth";
import { useFetch } from "../lib/hooks";
import type { AccessLog, IssuedCredential } from "../lib/types";

export default function MyPass() {
  const { user } = useAuth();
  const { data: credential, error } = useFetch<IssuedCredential>("/api/qr/me");
  const { data: logs } = useFetch<AccessLog[]>(
    user?.employee_id ? `/api/employees/${user.employee_id}/access-logs?limit=20` : null,
  );

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="My pass" subtitle="Show this QR at the gate" />
      {error && <Alert kind="info">{error}</Alert>}
      {credential && (
        <div className="card p-4">
          <PassShare
            credential={credential}
            title={user?.full_name ?? "Employee pass"}
            message={`Employee pass for ${user?.full_name}.`}
          />
        </div>
      )}

      {logs && logs.length > 0 && (
        <div className="card mt-6">
          <p className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">
            My recent access
          </p>
          <ul className="divide-y divide-slate-100 text-sm">
            {logs.map((log) => (
              <li key={log.id} className="flex justify-between px-4 py-2">
                <span>
                  {formatDateTime(log.occurred_at)} · {log.gate_name}
                </span>
                <span className={log.status === "GRANTED" ? "text-emerald-600" : "text-rose-600"}>
                  {log.direction ?? log.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
