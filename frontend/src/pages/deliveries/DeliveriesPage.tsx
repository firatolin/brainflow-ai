import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { toast } from "sonner";
import { deliveriesApi, vehiclesApi, type DeliveryStatus, type DeliveryPriority, type DeliveryCreateInput } from "@/api/endpoints";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { DeliveryStatusBadge, DeliveryPriorityBadge, RiskScoreBadge } from "@/components/shared/StatusBadge";
import { DeliveryFormDialog } from "@/pages/deliveries/DeliveryFormDialog";

const PAGE_SIZE = 20;

export default function DeliveriesPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<string>("");
  const [priority, setPriority] = useState<string>("");
  const [vehicleFilter, setVehicleFilter] = useState<string>("");
  const [createOpen, setCreateOpen] = useState(false);

  const vehicles = useQuery({
    queryKey: ["vehicles-lookup"],
    queryFn: () => vehiclesApi.list({ page_size: 100 }),
    staleTime: 60_000,
  });

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["deliveries", page, q, status, priority, vehicleFilter],
    queryFn: () =>
      deliveriesApi.list({
        page,
        page_size: PAGE_SIZE,
        q: q || undefined,
        status: status || undefined,
        priority: priority || undefined,
        vehicle_id: vehicleFilter ? Number(vehicleFilter) : undefined,
        sort: "created_at",
        order: "desc",
      }),
  });

  const qc = useQueryClient();
  const createMutation = useMutation({
    mutationFn: (input: DeliveryCreateInput) => deliveriesApi.create(input),
    onSuccess: () => {
      toast.success("Delivery created");
      qc.invalidateQueries({ queryKey: ["deliveries"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
      setCreateOpen(false);
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Create failed"),
  });

  const vehicleLookup = new Map((vehicles.data?.items ?? []).map((v) => [v.id, v]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Deliveries</h1>
          <p className="text-sm text-muted-foreground">
            {data?.total ?? 0} total · demonstration data
          </p>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" /> New delivery
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-64">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search tracking, customer, destination"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
            className="pl-8"
          />
        </div>
        <Select value={status || "all"} onValueChange={(v) => { setStatus(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-40"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {(["pending", "assigned", "in_transit", "delayed", "delivered", "failed", "cancelled"] as DeliveryStatus[]).map((s) => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={priority || "all"} onValueChange={(v) => { setPriority(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-40"><SelectValue placeholder="Priority" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All priorities</SelectItem>
            {(["low", "normal", "high", "urgent"] as DeliveryPriority[]).map((p) => (
              <SelectItem key={p} value={p}>{p}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={vehicleFilter || "all"} onValueChange={(v) => { setVehicleFilter(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-44"><SelectValue placeholder="Vehicle" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All vehicles</SelectItem>
            {(vehicles.data?.items ?? []).map((v) => (
              <SelectItem key={v.id} value={String(v.id)}>{v.code}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border bg-white">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : isError ? (
          <div className="p-4 text-sm text-red-700">
            Failed to load: {error instanceof Error ? error.message : "unknown error"}
          </div>
        ) : (data?.items.length ?? 0) === 0 ? (
          <div className="p-8 text-center text-sm text-muted-foreground">
            No deliveries match the current filters.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50/60 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-2 font-medium">Tracking</th>
                <th className="px-4 py-2 font-medium">Destination</th>
                <th className="px-4 py-2 font-medium">Priority</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Risk</th>
                <th className="px-4 py-2 font-medium">Vehicle</th>
                <th className="px-4 py-2 font-medium">Deadline</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((d) => (
                <tr
                  key={d.id}
                  onClick={() => navigate(`/deliveries/${d.id}`)}
                  className="cursor-pointer border-b last:border-b-0 hover:bg-slate-50"
                >
                  <td className="px-4 py-2 font-mono text-xs">{d.tracking_number}</td>
                  <td className="px-4 py-2 text-slate-700">{d.destination}</td>
                  <td className="px-4 py-2"><DeliveryPriorityBadge priority={d.priority} /></td>
                  <td className="px-4 py-2"><DeliveryStatusBadge status={d.status} /></td>
                  <td className="px-4 py-2"><RiskScoreBadge score={d.risk_score} /></td>
                  <td className="px-4 py-2 text-slate-700">
                    {d.vehicle_id ? vehicleLookup.get(d.vehicle_id)?.code ?? `#${d.vehicle_id}` : <span className="text-muted-foreground">—</span>}
                  </td>
                  <td className="px-4 py-2 text-slate-700 tabular-nums">
                    {new Date(d.promised_deadline).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="flex items-center justify-between border-t px-4 py-2 text-xs text-muted-foreground">
          <span>Page {data?.page ?? 1} of {Math.max(1, data?.pages ?? 1)}</span>
          <div className="flex gap-2">
            <Button
              variant="outline" size="sm"
              disabled={(data?.page ?? 1) <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              ← Prev
            </Button>
            <Button
              variant="outline" size="sm"
              disabled={(data?.page ?? 1) >= (data?.pages ?? 1)}
              onClick={() => setPage((p) => p + 1)}
            >
              Next →
            </Button>
          </div>
        </div>
      </div>

      <DeliveryFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        submitting={createMutation.isPending}
        onSubmit={(input) => createMutation.mutate(input)}
        vehicles={vehicles.data?.items ?? []}
      />
    </div>
  );
}
