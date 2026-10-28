import { cn } from "@/lib/utils";

type Risk = { low: number; medium: number; high: number; critical: number };

const ITEMS: Array<{ key: keyof Risk; label: string; color: string }> = [
  { key: "low", label: "Low", color: "bg-slate-300" },
  { key: "medium", label: "Medium", color: "bg-amber-400" },
  { key: "high", label: "High", color: "bg-orange-500" },
  { key: "critical", label: "Critical", color: "bg-red-600" },
];

export function RiskBars({ data }: { data: Risk }) {
  const total = data.low + data.medium + data.high + data.critical;
  return (
    <div className="space-y-3">
      {ITEMS.map((it) => {
        const count = data[it.key];
        const pct = total > 0 ? (count / total) * 100 : 0;
        return (
          <div key={it.key}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-slate-700">{it.label}</span>
              <span className="tabular-nums text-muted-foreground">
                {count} <span className="text-slate-400">({pct.toFixed(0)}%)</span>
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div className={cn("h-full rounded-full", it.color)} style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
      {total === 0 && (
        <div className="text-xs text-muted-foreground">No active deliveries.</div>
      )}
    </div>
  );
}
