import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, FileText } from "lucide-react";
import { toast } from "sonner";
import { deliveriesApi, vehiclesApi, customerDraftsApi, type DeliveryStatus } from "@/api/endpoints";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { DeliveryStatusBadge, DeliveryPriorityBadge, RiskScoreBadge } from "@/components/shared/StatusBadge";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

const VALID_NEXT: Record<DeliveryStatus, DeliveryStatus[]> = {
  pending: ["assigned", "cancelled"],
  assigned: ["in_transit", "pending", "cancelled"],
  in_transit: ["delivered", "delayed", "failed"],
  delayed: ["delivered", "failed", "in_transit"],
  delivered: [],
  failed: [],
  cancelled: [],
};

export default function DeliveryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const deliveryId = Number(id);
  const qc = useQueryClient();

  const delivery = useQuery({
    queryKey: ["delivery", deliveryId],
    queryFn: () => deliveriesApi.get(deliveryId),
    enabled: Number.isFinite(deliveryId),
  });
  const history = useQuery({
    queryKey: ["delivery-history", deliveryId],
    queryFn: () => deliveriesApi.history(deliveryId),
    enabled: Number.isFinite(deliveryId),
  });
  const vehicles = useQuery({
    queryKey: ["vehicles-lookup"],
    queryFn: () => vehiclesApi.list({ page_size: 100 }),
    staleTime: 60_000,
  });

  const assignMut = useMutation({
    mutationFn: (vehicle_id: number | null) => deliveriesApi.assign(deliveryId, vehicle_id),
    onSuccess: () => {
      toast.success("Assignment updated");
      qc.invalidateQueries({ queryKey: ["delivery", deliveryId] });
      qc.invalidateQueries({ queryKey: ["delivery-history", deliveryId] });
      qc.invalidateQueries({ queryKey: ["deliveries"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Assign failed"),
  });

  const statusMut = useMutation({
    mutationFn: (s: DeliveryStatus) => deliveriesApi.status(deliveryId, s),
    onSuccess: () => {
      toast.success("Status updated");
      qc.invalidateQueries({ queryKey: ["delivery", deliveryId] });
      qc.invalidateQueries({ queryKey: ["delivery-history", deliveryId] });
      qc.invalidateQueries({ queryKey: ["deliveries"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Status change failed"),
  });

  const draftMut = useMutation({
    mutationFn: () => customerDraftsApi.get(deliveryId),
    onSuccess: (draft) => {
      toast.success("Draft ready", { description: draft.reason });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Draft failed"),
  });

  if (delivery.isLoading) {
    return <div className="space-y-3"><Skeleton className="h-10 w-72" /><Skeleton className="h-64 w-full" /></div>;
  }
  if (delivery.isError || !delivery.data) {
    return <div className="text-sm text-red-700">Failed to load delivery.</div>;
  }

  const d = delivery.data;
  const nextStatuses = VALID_NEXT[d.status] ?? [];
  const canReassign = !["delivered", "failed", "cancelled"].includes(d.status);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/deliveries" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-slate-800">
            <ArrowLeft className="h-3.5 w-3.5" /> Deliveries
          </Link>
          <h1 className="mt-1 font-mono text-xl font-semibold">{d.tracking_number}</h1>
          <p className="text-sm text-muted-foreground">{d.customer_ref} · {d.destination}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => draftMut.mutate()} disabled={draftMut.isPending}>
            <FileText className="h-4 w-4" /> Draft customer message
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-lg border bg-white p-4 md:col-span-2">
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div><span className="text-xs uppercase tracking-wide text-muted-foreground">Priority</span><div className="mt-1"><DeliveryPriorityBadge priority={d.priority} /></div></div>
            <div><span className="text-xs uppercase tracking-wide text-muted-foreground">Status</span><div className="mt-1"><DeliveryStatusBadge status={d.status} /></div></div>
            <div><span className="text-xs uppercase tracking-wide text-muted-foreground">Risk</span><div className="mt-1"><RiskScoreBadge score={d.risk_score} /></div></div>
            <div><span className="text-xs uppercase tracking-wide text-muted-foreground">Vehicle</span><div className="mt-1">{d.vehicle_id ? `#${d.vehicle_id}` : "—"}</div></div>
            <div><span className="text-xs uppercase tracking-wide text-muted-foreground">Dispatch</span><div className="mt-1 tabular-nums">{new Date(d.scheduled_dispatch).toLocaleString()}</div></div>
            <div><span className="text-xs uppercase tracking-wide text-muted-foreground">Deadline</span><div className="mt-1 tabular-nums">{new Date(d.promised_deadline).toLocaleString()}</div></div>
            <div><span className="text-xs uppercase tracking-wide text-muted-foreground">Distance</span><div className="mt-1">{d.distance_km.toFixed(1)} km</div></div>
            <div><span className="text-xs uppercase tracking-wide text-muted-foreground">Cost est.</span><div className="mt-1">{d.cost_estimate.toFixed(2)}</div></div>
          </div>
          {d.risk_explanation && (
            <div className="mt-4 rounded-md border bg-slate-50 p-3 text-xs text-slate-700">
              <div className="font-medium">Risk assessment</div>
              <div className="mt-1 text-muted-foreground">{d.risk_explanation}</div>
            </div>
          )}
        </div>

        <div className="space-y-3">
          {canReassign && (
            <div className="rounded-lg border bg-white p-4">
              <div className="mb-2 text-sm font-medium">Assignment</div>
              <Select
                value={d.vehicle_id ? String(d.vehicle_id) : "none"}
                onValueChange={(v) => assignMut.mutate(v === "none" ? null : Number(v))}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Unassigned</SelectItem>
                  {(vehicles.data?.items ?? []).filter((v) => v.available).map((v) => (
                    <SelectItem key={v.id} value={String(v.id)}>{v.code}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          {nextStatuses.length > 0 && (
            <div className="rounded-lg border bg-white p-4">
              <div className="mb-2 text-sm font-medium">Change status</div>
              <div className="flex flex-wrap gap-2">
                {nextStatuses.map((s) => (
                  <ConfirmDialog
                    key={s}
                    title={`Change status to '${s}'?`}
                    description="This action will be recorded in the delivery history."
                    confirmLabel="Change"
                    onConfirm={() => statusMut.mutateAsync(s)}
                  >
                    {(open) => (
                      <Button size="sm" variant="outline" onClick={open}>
                        → {s}
                      </Button>
                    )}
                  </ConfirmDialog>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-lg border bg-white">
        <div className="border-b px-4 py-2.5">
          <h2 className="text-sm font-medium">History</h2>
        </div>
        {history.isLoading ? (
          <div className="p-4"><Skeleton className="h-16 w-full" /></div>
        ) : (history.data?.length ?? 0) === 0 ? (
          <div className="p-4 text-xs text-muted-foreground">No history yet.</div>
        ) : (
          <ul className="divide-y">
            {history.data!.map((h) => (
              <li key={h.id} className="px-4 py-2 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <span className="font-medium">{h.event_type}</span>
                    {h.from_status || h.to_status ? (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {h.from_status ?? "—"} → {h.to_status ?? "—"}
                      </span>
                    ) : null}
                    {h.note && <span className="ml-2 text-xs text-muted-foreground">· {h.note}</span>}
                  </div>
                  <div className="text-xs text-muted-foreground tabular-nums">
                    {new Date(h.created_at).toLocaleString()}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
