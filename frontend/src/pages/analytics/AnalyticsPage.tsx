import { useQuery } from "@tanstack/react-query";
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
  Line, LineChart,
} from "recharts";
import { analyticsApi } from "@/api/endpoints";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

export default function AnalyticsPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: analyticsApi.summary,
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-56" />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}
        </div>
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }
  if (isError || !data) {
    return <div className="text-sm text-red-700">Failed to load analytics: {error instanceof Error ? error.message : "unknown"}</div>;
  }

  const m = data.measured;
  const riskRows = [
    { label: "Low", value: data.estimated.risk_distribution.low },
    { label: "Medium", value: data.estimated.risk_distribution.medium },
    { label: "High", value: data.estimated.risk_distribution.high },
    { label: "Critical", value: data.estimated.risk_distribution.critical },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground">
          Measured outcomes + rule-based estimates · demonstration data
        </p>
      </div>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="Total deliveries" value={m.total_deliveries} />
        <Kpi label="Delivered" value={m.delivered} />
        <Kpi
          label="On-time rate"
          value={m.on_time_rate_pct === null ? "—" : `${m.on_time_rate_pct.toFixed(1)}%`}
        />
        <Kpi
          label="Delay rate"
          value={m.delay_rate_pct === null ? "—" : `${m.delay_rate_pct.toFixed(1)}%`}
        />
        <Kpi
          label="Completion rate"
          value={m.completion_rate_pct === null ? "—" : `${m.completion_rate_pct.toFixed(1)}%`}
        />
        <Kpi
          label="Avg delay"
          value={m.avg_delay_minutes === null ? "—" : `${m.avg_delay_minutes.toFixed(1)} min`}
        />
        <Kpi
          label="Cost (active)"
          value={m.cost_estimate_active.toFixed(2)}
        />
        <Kpi
          label="Cost (delivered)"
          value={m.cost_estimate_delivered.toFixed(2)}
        />
      </section>

      <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded-lg border bg-white p-4">
          <h2 className="text-sm font-medium">Risk distribution</h2>
          <p className="text-xs text-muted-foreground">Active deliveries</p>
          <div className="mt-3 h-64">
            <ResponsiveContainer>
              <BarChart data={riskRows} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                <CartesianGrid stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#64748b" }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#64748b" }} allowDecimals={false} />
                <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }} />
                <Bar dataKey="value" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg border bg-white p-4">
          <h2 className="text-sm font-medium">14-day trend</h2>
          <p className="text-xs text-muted-foreground">Delivered vs incidents</p>
          <div className="mt-3 h-64">
            <ResponsiveContainer>
              <LineChart data={data.trend_14d} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                <CartesianGrid stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "#64748b" }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#64748b" }} allowDecimals={false} />
                <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }} />
                <Line type="monotone" dataKey="delivered" name="Delivered" stroke="#10b981" strokeWidth={1.5} dot={false} />
                <Line type="monotone" dataKey="incidents" name="Incidents" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded-lg border bg-white p-4">
          <h2 className="text-sm font-medium">Vehicle utilization</h2>
          <p className="text-xs text-muted-foreground">Active deliveries / capacity</p>
          <ul className="mt-3 divide-y">
            {data.estimated.vehicle_utilization.map((v) => (
              <li key={v.vehicle_id} className="flex items-center justify-between py-2 text-sm">
                <span className="font-mono text-xs">{v.code}</span>
                <div className="flex items-center gap-3">
                  <div className="h-1 w-28 overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-slate-400" style={{ width: `${v.utilization_pct}%` }} />
                  </div>
                  <span className="w-14 text-right text-xs tabular-nums text-muted-foreground">
                    {v.active}/{v.capacity}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-lg border bg-white p-4">
          <h2 className="text-sm font-medium">Incidents</h2>
          <p className="text-xs text-muted-foreground">
            Avg resolution:{" "}
            {data.incidents.avg_resolution_minutes === null
              ? "—"
              : `${data.incidents.avg_resolution_minutes.toFixed(1)} min`}
          </p>
          <ul className="mt-3 divide-y text-sm">
            {Object.entries(data.incidents.by_kind).map(([k, v]) => (
              <li key={k} className="flex justify-between py-1.5">
                <span className="font-mono text-xs text-slate-700">{k}</span>
                <span className="tabular-nums">{v}</span>
              </li>
            ))}
            {Object.keys(data.incidents.by_kind).length === 0 && (
              <li className="text-xs text-muted-foreground">No incidents recorded.</li>
            )}
          </ul>
        </div>
      </section>

      <section className="rounded-lg border bg-white p-4">
        <h2 className="text-sm font-medium">Plan comparison (latest)</h2>
        <p className="text-xs text-muted-foreground">Deterministic optimizer · compare baseline vs alternatives</p>
        {data.plans.length === 0 ? (
          <div className="mt-3 text-xs text-muted-foreground">No plans yet.</div>
        ) : (
          <div className="mt-3 overflow-hidden rounded-md border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50/60 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-3 py-2">Kind</th>
                  <th className="px-3 py-2">Feasible</th>
                  <th className="px-3 py-2">Late</th>
                  <th className="px-3 py-2">Delay (min)</th>
                  <th className="px-3 py-2">Extra cost</th>
                  <th className="px-3 py-2">Changes</th>
                </tr>
              </thead>
              <tbody>
                {data.plans.map((p) => (
                  <tr key={p.id} className="border-b last:border-b-0">
                    <td className="px-3 py-1.5 font-mono text-xs">{p.kind}</td>
                    <td className="px-3 py-1.5"><Badge variant={p.feasible ? "success" : "danger"}>{p.feasible ? "yes" : "no"}</Badge></td>
                    <td className="px-3 py-1.5 tabular-nums">{p.late_count}</td>
                    <td className="px-3 py-1.5 tabular-nums">{p.total_delay_minutes.toFixed(0)}</td>
                    <td className="px-3 py-1.5 tabular-nums">{p.extra_cost.toFixed(2)}</td>
                    <td className="px-3 py-1.5 tabular-nums">{p.changes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}
