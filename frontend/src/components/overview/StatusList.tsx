type Statuses = Record<string, number>;

const LABELS: Record<string, string> = {
  pending: "Pending",
  assigned: "Assigned",
  in_transit: "In transit",
  delayed: "Delayed",
  delivered: "Delivered",
  failed: "Failed",
  cancelled: "Cancelled",
};

export function StatusList({ data }: { data: Statuses }) {
  const entries = Object.entries(data).filter(([, v]) => v > 0);
  const total = entries.reduce((acc, [, v]) => acc + v, 0);

  if (entries.length === 0) {
    return <div className="text-xs text-muted-foreground">No deliveries yet.</div>;
  }

  return (
    <div className="divide-y">
      {entries.map(([k, v]) => {
        const pct = total > 0 ? (v / total) * 100 : 0;
        return (
          <div key={k} className="flex items-center justify-between py-2">
            <span className="text-sm text-slate-700">{LABELS[k] ?? k}</span>
            <div className="flex items-center gap-3">
              <div className="h-1 w-24 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-slate-400" style={{ width: `${pct}%` }} />
              </div>
              <span className="w-8 text-right text-sm tabular-nums text-slate-700">{v}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
