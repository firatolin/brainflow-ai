import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, Send, CheckCircle2, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { plansApi, type RecoveryPlan } from "@/api/endpoints";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

export default function RecoveryPage() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const list = useQuery({
    queryKey: ["plans"],
    queryFn: () => plansApi.list({ page_size: 30 }),
  });

  const generateMut = useMutation({
    mutationFn: plansApi.generate,
    onSuccess: (plans) => {
      toast.success(`Generated ${plans.length} plans`);
      qc.invalidateQueries({ queryKey: ["plans"] });
      if (plans[0]) setSelectedId(plans[0].id);
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Generate failed"),
  });

  const submitMut = useMutation({
    mutationFn: (id: number) => plansApi.submit(id),
    onSuccess: () => {
      toast.success("Plan submitted for approval");
      qc.invalidateQueries({ queryKey: ["plans"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Submit failed"),
  });

  const plans = list.data?.items ?? [];
  const latest = latestBundle(plans);
  const selected = selectedId ? plans.find((p) => p.id === selectedId) ?? null : null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Recovery planning</h1>
          <p className="text-sm text-muted-foreground">
            Deterministic rule-based optimizer · compares alternatives against baseline
          </p>
        </div>
        <Button size="sm" onClick={() => generateMut.mutate()} disabled={generateMut.isPending}>
          <Play className="h-4 w-4" /> {generateMut.isPending ? "Generating…" : "Generate plans"}
        </Button>
      </div>

      {list.isLoading ? (
        <div className="space-y-2"><Skeleton className="h-40 w-full" /></div>
      ) : plans.length === 0 ? (
        <div className="rounded-lg border bg-white p-8 text-center text-sm text-muted-foreground">
          No plans yet. Click <span className="font-medium">Generate plans</span> to build a baseline, minimize-delays, and balanced option from current data.
        </div>
      ) : (
        <>
          {latest && (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {latest.map((p) => (
                <PlanCard
                  key={p.id}
                  plan={p}
                  onSelect={() => setSelectedId(p.id)}
                  selected={selectedId === p.id}
                />
              ))}
            </div>
          )}

          {selected && (
            <div className="rounded-lg border bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{selected.kind}</span>
                    <Badge variant={selected.feasible ? "success" : "danger"}>
                      {selected.feasible ? "feasible" : "infeasible"}
                    </Badge>
                    <Badge variant="muted">{selected.status}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{selected.explanation}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {selected.feasible && selected.status === "draft" && (
                    <ConfirmDialog
                      title="Submit this plan for approval?"
                      description="A pending approval will be created. A reviewer must approve before it can be executed."
                      confirmLabel="Submit for approval"
                      onConfirm={() => submitMut.mutateAsync(selected.id)}
                    >
                      {(open) => (
                        <Button size="sm" onClick={open}>
                          <Send className="h-4 w-4" /> Submit for approval
                        </Button>
                      )}
                    </ConfirmDialog>
                  )}
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-5 text-sm">
                <Metric label="Late deliveries" value={selected.expected_late_count} />
                <Metric label="Total delay (min)" value={selected.expected_total_delay_minutes.toFixed(0)} />
                <Metric label="Priority-weighted" value={selected.expected_priority_weighted_delay.toFixed(0)} />
                <Metric label="Extra cost" value={selected.expected_cost.toFixed(2)} />
                <Metric label="Changes" value={selected.changes_count} />
              </div>

              {selected.items.length > 0 && (
                <div className="mt-4 overflow-hidden rounded-md border">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-slate-50/60 text-left text-xs uppercase tracking-wide text-muted-foreground">
                        <th className="px-3 py-2 font-medium">Delivery</th>
                        <th className="px-3 py-2 font-medium">From</th>
                        <th className="px-3 py-2 font-medium">To</th>
                        <th className="px-3 py-2 font-medium">Exp. delay</th>
                        <th className="px-3 py-2 font-medium">Late?</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected.items.slice(0, 30).map((it) => (
                        <tr key={it.id} className="border-b last:border-b-0">
                          <td className="px-3 py-1.5 font-mono text-xs">#{it.delivery_id}</td>
                          <td className="px-3 py-1.5">{it.from_vehicle_id ?? "—"}</td>
                          <td className="px-3 py-1.5">{it.to_vehicle_id ?? "—"}</td>
                          <td className="px-3 py-1.5 tabular-nums">{it.expected_delay_minutes.toFixed(0)}m</td>
                          <td className="px-3 py-1.5">
                            {it.expected_late ? <Badge variant="warning">late</Badge> : <Badge variant="muted">on-time</Badge>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-0.5 text-base font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function PlanCard({ plan, onSelect, selected }: { plan: RecoveryPlan; onSelect: () => void; selected: boolean }) {
  return (
    <button
      onClick={onSelect}
      className={`rounded-lg border bg-white p-4 text-left transition-colors ${
        selected ? "border-primary ring-2 ring-primary/20" : "hover:border-slate-300"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{plan.kind}</span>
        {plan.feasible ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
        ) : (
          <AlertCircle className="h-4 w-4 text-red-600" />
        )}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
        <div>Late: <span className="text-slate-800 font-medium tabular-nums">{plan.expected_late_count}</span></div>
        <div>Delay: <span className="text-slate-800 font-medium tabular-nums">{plan.expected_total_delay_minutes.toFixed(0)}m</span></div>
        <div>Cost: <span className="text-slate-800 font-medium tabular-nums">{plan.expected_cost.toFixed(2)}</span></div>
        <div>Changes: <span className="text-slate-800 font-medium tabular-nums">{plan.changes_count}</span></div>
      </div>
    </button>
  );
}

function latestBundle(plans: RecoveryPlan[]): RecoveryPlan[] {
  // Group by "created_at minute" — take the three most recent from same generation
  if (plans.length === 0) return [];
  const newest = plans[0];
  const minute = newest.created_at.slice(0, 16);
  return plans.filter((p) => p.created_at.slice(0, 16) === minute).slice(0, 3);
}
