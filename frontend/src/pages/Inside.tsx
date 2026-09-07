import { Empty, PageHeader, StatCard } from "../components/ui";
import { download } from "../lib/api";
import { formatDateTime, humanise } from "../lib/format";
import { useFetch } from "../lib/hooks";
import { useAuth } from "../lib/auth";
import type { CurrentlyInside } from "../lib/types";

export default function Inside() {
  const { can } = useAuth();
  const { data, reload } = useFetch<CurrentlyInside>("/api/access/currently-inside");

  return (
    <div>
      <PageHeader
        title="Currently inside"
        subtitle="Live occupancy — also the evacuation list"
        actions={
          <>
            <button className="btn-secondary" onClick={reload}>
              Refresh
            </button>
            {can("ADMIN", "SUPER_ADMIN") && (
              <button
                className="btn-primary"
                onClick={() =>
                  download("/api/reports/currently-inside?format=pdf", "currently-inside.pdf")
                }
              >
                Export evacuation list
              </button>
            )}
          </>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Total inside" value={data?.total ?? "—"} />
        <StatCard label="Employees" value={data?.employees ?? "—"} />
        <StatCard label="Visitors" value={data?.visitors ?? "—"} />
        <StatCard label="Delivery personnel" value={data?.delivery ?? "—"} />
      </div>

      <div className="card mt-6 overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-100">
            <tr>
              <th className="th">Type</th>
              <th className="th">Reference</th>
              <th className="th">Name</th>
              <th className="th">Purpose</th>
              <th className="th">Host</th>
              <th className="th">Gate</th>
              <th className="th">Entered</th>
              <th className="th">Expected exit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data?.people.map((person) => (
              <tr key={`${person.subject_type}-${person.subject_id}`}>
                <td className="td">{humanise(person.subject_type)}</td>
                <td className="td font-mono text-xs">{person.subject_reference}</td>
                <td className="td font-medium text-slate-900">{person.subject_label}</td>
                <td className="td">{humanise(person.purpose)}</td>
                <td className="td">{person.host_label}</td>
                <td className="td">{person.gate_name}</td>
                <td className="td whitespace-nowrap">{formatDateTime(person.entered_at)}</td>
                <td className="td whitespace-nowrap">{formatDateTime(person.expected_exit_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.people.length === 0 && <Empty message="Nobody is inside the premises." />}
      </div>
    </div>
  );
}
