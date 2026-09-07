import { Link } from "react-router-dom";

import { Empty, PageHeader, StatCard, StatusBadge } from "../components/ui";
import { formatDateTime, humanise } from "../lib/format";
import { useFetch } from "../lib/hooks";
import type { DashboardStats } from "../lib/types";

export default function Dashboard() {
  const { data, error } = useFetch<DashboardStats>("/api/dashboard");

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Live view of access across every gate"
        actions={
          <Link className="btn-primary" to="/scan">
            Open gate verification
          </Link>
        }
      />
      {error && <p className="text-sm text-rose-600">{error}</p>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard label="Active employees" value={data?.employees ?? "—"} />
        <StatCard label="Visitors today" value={data?.visitors_today ?? "—"} />
        <StatCard label="Deliveries today" value={data?.deliveries_today ?? "—"} />
        <StatCard label="Currently inside" value={data?.currently_inside ?? "—"} tone="good" />
        <StatCard label="Denied today" value={data?.denied_today ?? "—"} tone="bad" />
      </div>

      <div className="card mt-6">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">Recent activity</h2>
          <Link className="text-sm text-brand-600 hover:underline" to="/logs">
            View all logs
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-slate-100">
              <tr>
                <th className="th">Time</th>
                <th className="th">Person</th>
                <th className="th">Type</th>
                <th className="th">Gate</th>
                <th className="th">Direction</th>
                <th className="th">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.recent_activity.map((log) => (
                <tr key={log.id}>
                  <td className="td whitespace-nowrap">{formatDateTime(log.occurred_at)}</td>
                  <td className="td">
                    <span className="font-medium text-slate-900">{log.subject_label}</span>
                    {log.subject_reference && (
                      <span className="ml-2 text-xs text-slate-400">{log.subject_reference}</span>
                    )}
                  </td>
                  <td className="td">{humanise(log.subject_type)}</td>
                  <td className="td">{log.gate_name}</td>
                  <td className="td">{humanise(log.direction)}</td>
                  <td className="td">
                    <StatusBadge value={log.status} />
                    {log.reason && (
                      <span className="ml-2 text-xs text-slate-500">{humanise(log.reason)}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data && data.recent_activity.length === 0 && <Empty message="No access events recorded yet." />}
        </div>
      </div>
    </div>
  );
}
