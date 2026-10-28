import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { vehiclesApi, type Vehicle, type VehicleStatus, type VehicleUpdateInput } from "@/api/endpoints";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { AvailableBadge } from "@/components/shared/StatusBadge";
import { VehicleFormDialog } from "@/pages/fleet/VehicleFormDialog";
import { VehicleEditDialog } from "@/pages/fleet/VehicleEditDialog";

const STATUS_VARIANT: Record<VehicleStatus, "success" | "info" | "warning" | "muted"> = {
  available: "success",
  on_route: "info",
  maintenance: "warning",
  out_of_service: "muted",
};

export default function FleetPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [editVehicle, setEditVehicle] = useState<Vehicle | null>(null);
  const qc = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["vehicles", statusFilter],
    queryFn: () => vehiclesApi.list({ page_size: 100, status: statusFilter || undefined }),
  });

  const createMut = useMutation({
    mutationFn: vehiclesApi.create,
    onSuccess: () => {
      toast.success("Vehicle created");
      qc.invalidateQueries({ queryKey: ["vehicles"] });
      setCreateOpen(false);
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Create failed"),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, input }: { id: number; input: VehicleUpdateInput }) =>
      vehiclesApi.patch(id, input),
    onSuccess: () => {
      toast.success("Vehicle updated");
      qc.invalidateQueries({ queryKey: ["vehicles"] });
      setEditVehicle(null);
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Update failed"),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Fleet</h1>
          <p className="text-sm text-muted-foreground">
            {data?.total ?? 0} vehicles · demonstration fleet
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
            <SelectTrigger className="w-44"><SelectValue placeholder="Filter status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="available">Available</SelectItem>
              <SelectItem value="on_route">On route</SelectItem>
              <SelectItem value="maintenance">Maintenance</SelectItem>
              <SelectItem value="out_of_service">Out of service</SelectItem>
            </SelectContent>
          </Select>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" /> New vehicle
          </Button>
        </div>
      </div>

      <div className="rounded-lg border bg-white">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        ) : isError ? (
          <div className="p-4 text-sm text-red-700">
            Failed to load: {error instanceof Error ? error.message : "unknown error"}
          </div>
        ) : (data?.items.length ?? 0) === 0 ? (
          <div className="p-8 text-center text-sm text-muted-foreground">No vehicles.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50/60 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-2 font-medium">Code</th>
                <th className="px-4 py-2 font-medium">Type</th>
                <th className="px-4 py-2 font-medium">Capacity</th>
                <th className="px-4 py-2 font-medium">Zone</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Available</th>
                <th className="px-4 py-2 font-medium">Cost / km</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((v) => (
                <tr key={v.id} className="border-b last:border-b-0">
                  <td className="px-4 py-2 font-mono text-xs">{v.code}</td>
                  <td className="px-4 py-2 text-slate-700">{v.vehicle_type}</td>
                  <td className="px-4 py-2 tabular-nums text-slate-700">{v.capacity}</td>
                  <td className="px-4 py-2 text-slate-700">{v.location_zone}</td>
                  <td className="px-4 py-2"><Badge variant={STATUS_VARIANT[v.status]}>{v.status}</Badge></td>
                  <td className="px-4 py-2"><AvailableBadge available={v.available} /></td>
                  <td className="px-4 py-2 tabular-nums text-slate-700">{v.cost_per_km.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right">
                    <Button size="sm" variant="outline" onClick={() => setEditVehicle(v)}>Edit</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <VehicleFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        submitting={createMut.isPending}
        onSubmit={(v) => createMut.mutate(v)}
      />
      <VehicleEditDialog
        vehicle={editVehicle}
        onOpenChange={(open) => !open && setEditVehicle(null)}
        submitting={updateMut.isPending}
        onSubmit={(id, input) => updateMut.mutate({ id, input })}
      />
    </div>
  );
}
