import { useState } from "react";

import { Alert, Empty, Field, PageHeader } from "../components/ui";
import { download } from "../lib/api";
import { useFetch } from "../lib/hooks";

interface ReportPayload {
  title: string;
  headers: string[];
  rows: string[][];
}

const REPORTS = [
  { key: "access", label: "Daily access" },
  { key: "deliveries", label: "Deliveries" },
  { key: "visitors", label: "Visitors" },
  { key: "denied", label: "Denied access" },
  { key: "gate-wise", label: "Gate-wise" },
  { key: "entry-exit", label: "Entry / exit" },
  { key: "currently-inside", label: "Currently inside" },
];

const RANGE_FREE = new Set(["gate-wise", "currently-inside"]);

export default function Reports() {
  const today = new Date().toISOString().slice(0, 10);
  const [report, setReport] = useState("access");
  const [from, setFrom] = useState(today);
  const [to, setTo] = useState(today);
  const [error, setError] = useState<string | null>(null);

  const query = new URLSearchParams();
  if (!RANGE_FREE.has(report)) {
    query.set("date_from", from);
    query.set("date_to", to);
  }
  const { data } = useFetch<ReportPayload>(`/api/reports/${report}?${query}`, [report, from, to]);

  const exportAs = async (format: "csv" | "pdf") => {
    setError(null);
    const exportQuery = new URLSearchParams(query);
    exportQuery.set("format", format);
    try {
      await download(`/api/reports/${report}?${exportQuery}`, `${report}-report.${format}`);
    } catch (cause) {
      setError((cause as Error).message);
    }
  };

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Export access, visitor and delivery activity"
        actions={
          <>
            <button className="btn-secondary" onClick={() => exportAs("csv")}>
              Export CSV
            </button>
            <button className="btn-primary" onClick={() => exportAs("pdf")}>
              Export PDF
            </button>
          </>
        }
      />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="w-56">
          <Field label="Report">
            <select className="input" value={report} onChange={(event) => setReport(event.target.value)}>
              {REPORTS.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {!RANGE_FREE.has(report) && (
          <>
            <div className="w-44">
              <Field label="From">
                <input className="input" type="date" value={from} onChange={(event) => setFrom(event.target.value)} />
              </Field>
            </div>
            <div className="w-44">
              <Field label="To">
                <input className="input" type="date" value={to} onChange={(event) => setTo(event.target.value)} />
              </Field>
            </div>
          </>
        )}
      </div>

      {error && <Alert kind="error">{error}</Alert>}

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-100">
            <tr>
              {data?.headers.map((header) => (
                <th key={header} className="th">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data?.rows.map((row, index) => (
              <tr key={index}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className="td whitespace-nowrap">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.rows.length === 0 && <Empty message="No data for this period." />}
      </div>
    </div>
  );
}