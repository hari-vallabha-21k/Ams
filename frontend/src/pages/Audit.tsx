import { useState } from "react";

import { Empty, PageHeader } from "../components/ui";
import { formatDateTime, humanise } from "../lib/format";
import { useFetch } from "../lib/hooks";
import type { AuditEntry, Page } from "../lib/types";

export default function Audit() {
  const [action, setAction] = useState("");
  const [entity, setEntity] = useState("");
  const query = new URLSearchParams({ limit: "100" });
  if (action) query.set("action", action);
  if (entity) query.set("entity", entity);
  const { data } = useFetch<Page<AuditEntry>>(`/api/audit-logs?${query}`, [action, entity]);

  return (
    <div>
      <PageHeader title="Audit trail" subtitle="Who did what, and when" />

      <div className="mb-3 flex flex-wrap gap-2">
        <input
          className="input max-w-xs"
          placeholder="Filter by action, e.g. CREATE_DELIVERY"
          value={action}
          onChange={(event) => setAction(event.target.value.toUpperCase())}
        />
        <input
          className="input max-w-xs"
          placeholder="Filter by entity, e.g. delivery"
          value={entity}
          onChange={(event) => setEntity(event.target.value.toLowerCase())}
        />
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-100">
            <tr>
              <th className="th">Time</th>
              <th className="th">User</th>
              <th className="th">Action</th>
              <th className="th">Entity</th>
              <th className="th">ID</th>
              <th className="th">IP</th>
              <th className="th">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data?.items.map((entry) => (
              <tr key={entry.id}>
                <td className="td whitespace-nowrap">{formatDateTime(entry.created_at)}</td>
                <td className="td">{entry.user_label}</td>
                <td className="td font-medium text-slate-900">{humanise(entry.action)}</td>
                <td className="td">{humanise(entry.entity)}</td>
                <td className="td font-mono text-xs">{entry.entity_id}</td>
                <td className="td font-mono text-xs">{entry.ip_address}</td>
                <td className="td max-w-md truncate text-xs text-slate-500">{entry.meta}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.items.length === 0 && <Empty message="No audit entries match these filters." />}
      </div>
    </div>
  );
}
