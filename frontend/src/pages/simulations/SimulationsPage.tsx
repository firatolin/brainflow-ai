import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { toast } from "sonner";
import {
  simulationsApi, vehiclesApi, deliveriesApi,
  type SimulationScenario, type Simulation,
} from "@/api/endpoints";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

const SCENARIOS: Array<{ value: SimulationScenario; label: string; description: string }> = [
  { value: "vehicle_unavailable", label: "Vehicle unavailable", description: "Mark a vehicle as unavailable and re-plan." },
  { value: "heavy_rain", label: "Heavy rain", description: "Increase weather exposure on all active deliveries." },
  { value: "urgent_added", label: "Urgent delivery added", description: "Inject a hypothetical urgent delivery." },
  { value: "capacity_change", label: "Capacity change", description: "Reduce a vehicle's capacity." },
  { value: "deadline_earlier", label: "Deadline moved earlier", description: "Pull a delivery deadline forward." },
  { value: "assignment_failed", label: "Assignment failed", description: "Fail an assignment and revert to pending." },
];

export default function SimulationsPage() {
  const [scenario, setScenario] = useState<SimulationScenario>("vehicle_unavailable");
  const [result, setResult] = useState<Simulation | null>(null);

  const vehicles = useQuery({
    queryKey: ["vehicles-lookup"],
    queryFn: () => vehiclesApi.list({ page_size: 100 }),
    staleTime: 60_000,
  });
  const deliveries = useQuery({
    queryKey: ["deliveries-lookup"],
    queryFn: () => deliveriesApi.list({ page_size: 100, status: "assigned" }),
    staleTime: 30_000,
  });

  const [vehicleId, setVehicleId] = useState<string>("");
  const [deliveryId, setDeliveryId] = useState<string>("");
  const [capacity, setCapacity] = useState<number>(2);
  const [minutesEarlier, setMinutesEarlier] = useState<number>(60);
  const [weatherDelta, setWeatherDelta] = useState<number>(0.5);

  const run = useMutation({
    mutationFn: () => {
      const params: Record<string, unknown> = {};
      if (scenario === "vehicle_unavailable" || scenario === "capacity_change") {
        if (!vehicleId) throw new Error("Select a vehicle");
        params.vehicle_id = Number(vehicleId);
        if (scenario === "capacity_change") params.capacity = capacity;
      } else if (scenario === "deadline_earlier" || scenario === "assignment_failed") {
        if (!deliveryId) throw new Error("Select a delivery");
        params.delivery_id = Number(deliveryId);
        if (scenario === "deadline_earlier") params.minutes_earlier = minutesEarlier;
      } else if (scenario === "heavy_rain") {
        params.weather_delta = weatherDelta;
      }
      return simulationsApi.create(scenario, params);
    },
    onSuccess: (r) => {
      setResult(r);
      toast.success("Simulation complete");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Simulation failed"),
  });

  const needsVehicle = scenario === "vehicle_unavailable" || scenario === "capacity_change";
  const needsDelivery = scenario === "deadline_earlier" || scenario === "assignment_failed";

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Simulations</h1>
        <p className="text-sm text-muted-foreground">
          What-if analysis · read-only · never mutates production state
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border bg-white p-4">
          <div className="text-sm font-medium">Scenario</div>
          <div className="mt-2 space-y-1.5">
            <Select value={scenario} onValueChange={(v) => setScenario(v as SimulationScenario)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {SCENARIOS.map((s) => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {SCENARIOS.find((s) => s.value === scenario)?.description}
            </p>
          </div>

          <div className="mt-4 space-y-3">
            {needsVehicle && (
              <div className="space-y-1.5">
                <Label>Vehicle</Label>
                <Select value={vehicleId} onValueChange={setVehicleId}>
                  <SelectTrigger><SelectValue placeholder="Pick a vehicle" /></SelectTrigger>
                  <SelectContent>
                    {(vehicles.data?.items ?? []).map((v) => (
                      <SelectItem key={v.id} value={String(v.id)}>{v.code}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            {scenario === "capacity_change" && (
              <div className="space-y-1.5">
                <Label>New capacity</Label>
                <Input type="number" min={0} value={capacity} onChange={(e) => setCapacity(Number(e.target.value))} />
              </div>
            )}
            {needsDelivery && (
              <div className="space-y-1.5">
                <Label>Delivery</Label>
                <Select value={deliveryId} onValueChange={setDeliveryId}>
                  <SelectTrigger><SelectValue placeholder="Pick a delivery" /></SelectTrigger>
                  <SelectContent>
                    {(deliveries.data?.items ?? []).slice(0, 50).map((d) => (
                      <SelectItem key={d.id} value={String(d.id)}>{d.tracking_number}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            {scenario === "deadline_earlier" && (
              <div className="space-y-1.5">
                <Label>Minutes earlier</Label>
                <Input type="number" min={1} value={minutesEarlier} onChange={(e) => setMinutesEarlier(Number(e.target.value))} />
              </div>
            )}
            {scenario === "heavy_rain" && (
              <div className="space-y-1.5">
                <Label>Weather delta (0–1)</Label>
                <Input type="number" step="0.05" min={0} max={1} value={weatherDelta} onChange={(e) => setWeatherDelta(Number(e.target.value))} />
              </div>
            )}
          </div>

          <div className="mt-4">
            <Button size="sm" onClick={() => run.mutate()} disabled={run.isPending}>
              <Play className="h-4 w-4" /> {run.isPending ? "Running…" : "Run simulation"}
            </Button>
          </div>
        </div>

        <div className="rounded-lg border bg-white p-4">
          <div className="text-sm font-medium">Result</div>
          {run.isPending ? (
            <Skeleton className="mt-3 h-40 w-full" />
          ) : !result ? (
            <div className="mt-3 text-xs text-muted-foreground">
              No simulation yet. Choose a scenario and click "Run simulation". Results are estimates only.
            </div>
          ) : (
            <SimulationResult sim={result} />
          )}
        </div>
      </div>
    </div>
  );
}

function SimulationResult({ sim }: { sim: Simulation }) {
  const baseline = safeParse(sim.baseline_metrics_json);
  const simulated = safeParse(sim.simulated_metrics_json);
  const diff = safeParse(sim.diff_json);

  return (
    <div className="mt-3 space-y-3">
      <div className="flex items-center gap-2">
        <Badge variant="info">{sim.scenario}</Badge>
        <span className="text-xs text-muted-foreground">#{sim.id}</span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <KV label="Baseline late" value={baseline.late_count ?? "—"} />
        <KV label="Simulated late" value={simulated.late_count ?? "—"} />
        <KV label="Baseline delay" value={fmt(baseline.total_delay_minutes)} />
        <KV label="Simulated delay" value={fmt(simulated.total_delay_minutes)} />
        <KV label="Δ late (no recovery)" value={fmt(diff.no_recovery_late_delta, true)} />
        <KV label="Δ delay (no recovery)" value={fmt(diff.no_recovery_delay_delta, true)} />
        <KV label="Δ late (with recovery)" value={fmt(diff.recovered_late_delta, true)} />
        <KV label="Δ delay (with recovery)" value={fmt(diff.recovered_delay_delta, true)} />
        <KV label="Recovered feasible" value={diff.recovered_feasible ? "yes" : "no"} />
        <KV label="Changes by recovery" value={diff.assignments_changed_by_recovery ?? 0} />
      </div>

      <p className="text-xs text-muted-foreground border-t pt-3">{sim.explanation}</p>
    </div>
  );
}

function KV({ label, value }: { label: string; value: unknown }) {
  const text = typeof value === "number" ? String(value) :
    typeof value === "string" ? value :
    value === null || value === undefined ? "—" :
    JSON.stringify(value);
  return (
    <div className="rounded-md border bg-slate-50 px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-0.5 text-sm tabular-nums">{text}</div>
    </div>
  );
}

function fmt(v: unknown, signed = false): string {
  if (typeof v !== "number") return String(v ?? "—");
  const s = v.toFixed(1);
  return signed && v > 0 ? `+${s}` : s;
}

function safeParse(s: string): Record<string, unknown> {
  try { return JSON.parse(s); } catch { return {}; }
}
