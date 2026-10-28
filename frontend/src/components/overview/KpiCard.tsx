import { cn } from "@/lib/utils";

type Props = {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "neutral" | "warning" | "danger" | "success";
  icon?: React.ComponentType<{ className?: string }>;
};

const TONE: Record<NonNullable<Props["tone"]>, { value: string; dot: string }> = {
  neutral: { value: "text-slate-900", dot: "bg-slate-300" },
  success: { value: "text-emerald-700", dot: "bg-emerald-500" },
  warning: { value: "text-amber-700", dot: "bg-amber-500" },
  danger: { value: "text-red-700", dot: "bg-red-500" },
};

export function KpiCard({ label, value, hint, tone = "neutral", icon: Icon }: Props) {
  const t = TONE[tone];
  return (
    <div className="rounded-lg border bg-white p-4 transition-colors hover:border-slate-300">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        {Icon ? (
          <Icon className="h-4 w-4 text-slate-400" />
        ) : (
          <span className={cn("h-1.5 w-1.5 rounded-full", t.dot)} />
        )}
      </div>
      <div className={cn("mt-2 text-2xl font-semibold tabular-nums tracking-tight", t.value)}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}
