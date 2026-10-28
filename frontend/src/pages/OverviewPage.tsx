import {
  AlertTriangle, CheckCircle2, Clock, Package, Scan, ShieldAlert,
  Truck, Hourglass,
} from "lucide-react";
import { useDashboard } from "@/hooks/useDashboard";
import { KpiCard } from "@/components/overview/KpiCard";
import { TrendChart } from "@/components/overview/TrendChart";
import { RiskBars } from "@/components/overview/RiskBars";
import { StatusList } from "@/components/overview/StatusList";
import { RecentEvents } from "@/components/overview/RecentEvents";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useQueryClient } from "@tanstack/react-query";
import { endpoints } from "@/api/endpoints";
import { toast } from "sonner";
import { useState } from "react";

export default function OverviewPage() {
  const { data, isLoading, isError, error, refetch, dataUpdatedAt } = useDashboard();
  const qc = useQueryClient();
  const [scanning, setScanning] = useState(false);

  const triggerScan = async () => {
    setScanning(true);
    try {
      const res = await endpoints.triggerScan();
      toast.success(
        `Scan complete: ${res.deliveries_scanned} scanned, ${res.incidents_created} new, ${res.incidents_auto_resolved} auto-resolved`,
      );
      await qc.invalidateQueries();
    } catch (err) {
      toast.error(`Scan failed: ${err instanceof Error ? err.message : "unknown"}`);
    } finally {
      setScanning(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-56" />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <Skeleton className="h-72 w-full lg:col-span-2" />
          <Skeleton className="h-72 w-full" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
        <div className="mb-2 font-medium">Failed to load the overview</div>
        <div className="text-xs">
          {error instanceof Error ? error.message : "Unknown error"}
        </div>
        <div className="mt-3">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const t = data.totals;
  const onTime = data.on_time_rate_pct;
  const delayExposureHours = data.estimated_delay_exposure_minutes / 60;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Operations overview</h1>
          <p className="text-sm text-muted-foreground">
            Demonstration data · refreshed{" "}
            {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : "just now"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <Clock className="h-4 w-4" /> Refresh
          </Button>
          <Button size="sm" onClick={triggerScan} disabled={scanning}>
            <Scan className="h-4 w-4" /> {scanning ? "Scanning…" : "Run scan"}
          </Button>
        </div>
      </div>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard label="Active deliveries" value={t.active_deliveries} hint={`${t.deliveries} total`} icon={Package} />
        <KpiCard
          label="At risk"
          value={t.at_risk}
          hint={t.critical_risk > 0 ? `${t.critical_risk} critical` : "risk ≥ 50"}
          tone={t.at_risk > 0 ? "warning" : "neutral"}
          icon={ShieldAlert}
        />
        <KpiCard
          label="Delayed"
          value={t.delayed}
          hint="currently delayed"
          tone={t.delayed > 0 ? "danger" : "neutral"}
          icon={AlertTriangle}
        />
        <KpiCard
          label="On-time rate"
          value={onTime === null ? "—" : `${onTime.toFixed(0)}%`}
          hint={`${t.delivered} delivered`}
          tone={onTime !== null && onTime >= 90 ? "success" : "neutral"}
          icon={CheckCircle2}
        />
        <KpiCard
          label="Active vehicles"
          value={data.fleet.active}
          hint={`${data.fleet.total} total`}
          icon={Truck}
        />
        <KpiCard
          label="Open incidents"
          value={data.incidents.open}
          hint={data.incidents.acknowledged > 0 ? `${data.incidents.acknowledged} acknowledged` : "awaiting triage"}
          tone={data.incidents.open > 0 ? "warning" : "neutral"}
          icon={AlertTriangle}
        />
        <KpiCard
          label="Pending approvals"
          value={data.pending_approvals}
          hint="awaiting decision"
          tone={data.pending_approvals > 0 ? "warning" : "neutral"}
          icon={Hourglass}
        />
        <KpiCard
          label="Delay exposure"
          value={delayExposureHours > 0 ? `${delayExposureHours.toFixed(1)}h` : "0h"}
          hint="estimated · rule-based"
          icon={Clock}
        />
      </section>

      <section className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="rounded-lg border bg-white p-4 lg:col-span-2">
          <div className="mb-3 flex items-baseline justify-between">
            <div>
              <h2 className="text-sm font-medium">Last 7 days</h2>
              <p className="text-xs text-muted-foreground">
                Deliveries created vs. delivered
              </p>
            </div>
          </div>
          <TrendChart data={data.trend_7d} />
        </div>

        <div className="rounded-lg border bg-white p-4">
          <div className="mb-3">
            <h2 className="text-sm font-medium">Risk distribution</h2>
            <p className="text-xs text-muted-foreground">Active deliveries</p>
          </div>
          <RiskBars data={data.distributions.risk} />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="rounded-lg border bg-white p-4">
          <div className="mb-3">
            <h2 className="text-sm font-medium">Status distribution</h2>
            <p className="text-xs text-muted-foreground">All deliveries</p>
          </div>
          <StatusList data={data.distributions.status} />
        </div>

        <div className="rounded-lg border bg-white p-4 lg:col-span-2">
          <div className="mb-3">
            <h2 className="text-sm font-medium">Recent activity</h2>
            <p className="text-xs text-muted-foreground">
              Append-only audit trail
            </p>
          </div>
          <RecentEvents events={data.recent_events} />
        </div>
      </section>
    </div>
  );
}
