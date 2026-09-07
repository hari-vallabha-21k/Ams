import { useState } from "react";

import { Empty, PageHeader, StatusBadge } from "../components/ui";
import { formatDateTime, humanise } from "../lib/format";
import { useFetch, useGates } from "../lib/hooks";
import type { AccessLog, Page } from "../lib/types";

export default function Logs() {
  const gates = useGates();
  const [filters, setFilters] = useState({
    search: "",
    subject_type: "",
    status_filter: "",
    gate_id: "",
    direction: "",
  });
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  Object.entries(filters).forEach(([key, value]) => value && query.set(key, value));
  const { data } = useFetch<Page<AccessLog>>(`/api/access/logs?${query}`, [
    JSON.stringify(filters),
    offset,
  ]);

  const update = (key: keyof typeof filters, value: string) => {
    setOffset(0);
    setFilters((current) => ({ ...current, [key]: value }));
  };

  return (
    <div>
      <PageHeader title="Access logs" subtitle="Every access attempt, granted or denied" />

      <div className="mb-3 flex flex-wrap gap-2">
        <input
          className="input max-w-xs"
          placeholder="Search person or reference"
          value={filters.search}
          onChange={(event) => update("search", event.target.value)}
        />
        <select className="input max-w-[160px]" value={filters.subject_type} onChange={(e) => update("subject_type", e.target.value)}>
          <option value="">All types</option>
          {["EMPLOYEE", "VISITOR", "DELIVERY"].map((value) => (
            <option key={value} value={value}>
              {humanise(value)}
            </option>
          ))}
        </select>
        <select className="input max-w-[160px]" value={filters.status_filter} onChange={(e) => update("status_filter", e.target.value)}>
          <option value="">All results</option>
          <option value="GRANTED">Granted</option>
          <option value="DENIED">Denied</option>
        </select>
        <select className="input max-w-[160px]" value={filters.direction} onChange={(e) => update("direction", e.target.value)}>
          <option value="">Any direction</option>
          <option value="ENTRY">Entry</option>
          <option value="EXIT">Exit</option>
        </select>
        <select className="input max-w-[200px]" value={filters.gate_id} onChange={(e) => update("gate_id", e.target.value)}>
          <option value="">All gates</option>
          {gates.map((gate) => (
            <option key={gate.id} value={gate.id}>
              {gate.name}
            </option>
          ))}
        </select>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-100">
            <tr>
              <th className="th">Time</th>
              <th className="th">Type</th>
              <th className="th">Reference</th>
              <th className="th">Person</th>
              <th className="th">Gate</th>
              <th className="th">Direction</th>
              <th className="th">Result</th>
              <th className="th">Reason</th>
              <th className="th">Verified by</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data?.items.map((log) => (
              <tr key={log.id}>
                <td className="td whitespace-nowrap">{formatDateTime(log.occurred_at)}</td>
                <td className="td">{humanise(log.subject_type)}</td>
                <td className="td font-mono text-xs">{log.subject_reference}</td>
                <td className="td font-medium text-slate-900">{log.subject_label}</td>
                <td className="td">{log.gate_name}</td>
                <td className="td">{humanise(log.direction)}</td>
                <td className="td">
                  <StatusBadge value={log.status} />
                </td>
                <td className="td">
                  {humanise(log.reason)}
                  {log.reason_note && <span className="block text-xs text-slate-400">{log.reason_note}</span>}
                </td>
                <td className="td">{log.verified_by_name}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.items.length === 0 && <Empty message="No access events match these filters." />}
      </div>

      {data && data.total > limit && (
        <div className="mt-3 flex items-center justify-between text-sm text-slate-500">
          <span>
            Showing {offset + 1}–{Math.min(offset + limit, data.total)} of {data.total}
          </span>
          <div className="flex gap-2">
            <button className="btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
              Previous
            </button>
            <button
              className="btn-secondary"
              disabled={offset + limit >= data.total}
              onClick={() => setOffset(offset + limit)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
