import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCcw, Check, X } from "lucide-react";
import { toast } from "sonner";
import { incidentsApi, type Incident, type IncidentSeverity, type IncidentStatus } from "@/api/endpoints";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

const SEVERITY_VARIANT: Record<IncidentSeverity, "muted" | "info" | "warning" | "danger"> = {
  low: "muted",
  medium: "info",
  high: "warning",
  critical: "danger",
};

const STATUS_VARIANT: Record<IncidentStatus, "info" | "warning" | "success"> = {
  open: "warning",
  acknowledged: "info",
  resolved: "success",
};

export default function ExceptionsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("open");
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const qc = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["incidents", statusFilter, severityFilter, page],
    queryFn: () =>
      incidentsApi.list({
        page,
        page_size: 20,
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        sort: "created_at",
        order: "desc",
      }),
  });

  const scanMut = useMutation({
    mutationFn: incidentsApi.scan,
    onSuccess: (res) => {
      toast.success(
        `Scan complete: ${res.deliveries_scanned} scanned, ${res.incidents_created} new, ${res.incidents_auto_resolved} auto-resolved`,
      );
      qc.invalidateQueries({ queryKey: ["incidents"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Scan failed"),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, status, note }: { id: number; status: IncidentStatus; note?: string }) =>
      incidentsApi.update(id, { status, resolution_note: note }),
    onSuccess: () => {
      toast.success("Incident updated");
      qc.invalidateQueries({ queryKey: ["incidents"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Update failed"),
  });

  const grouped = groupBySeverity(data?.items ?? []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Exceptions</h1>
          <p className="text-sm text-muted-foreground">
            {data?.total ?? 0} incidents · deduplicated across scans
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={severityFilter || "all"} onValueChange={(v) => { setSeverityFilter(v === "all" ? "" : v); setPage(1); }}>
            <SelectTrigger className="w-44"><SelectValue placeholder="Severity" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
            </SelectContent>
          </Select>
          <Select value={statusFilter || "all"} onValueChange={(v) => { setStatusFilter(v === "all" ? "" : v); setPage(1); }}>
            <SelectTrigger className="w-44"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="acknowledged">Acknowledged</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
            </SelectContent>
          </Select>
          <Button size="sm" onClick={() => scanMut.mutate()} disabled={scanMut.isPending}>
            <RefreshCcw className="h-4 w-4" /> {scanMut.isPending ? "Scanning…" : "Run scan"}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}</div>
      ) : isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Failed to load: {error instanceof Error ? error.message : "unknown"}
        </div>
      ) : (data?.items.length ?? 0) === 0 ? (
        <div className="rounded-lg border bg-white p-8 text-center text-sm text-muted-foreground">
          No incidents match the current filters. {statusFilter === "open" && "All clear."}
        </div>
      ) : (
        <div className="space-y-4">
          {(["critical", "high", "medium", "low"] as IncidentSeverity[]).map((sev) => {
            const items = grouped[sev];
            if (items.length === 0) return null;
            return (
              <div key={sev}>
                <div className="mb-2 flex items-center gap-2">
                  <Badge variant={SEVERITY_VARIANT[sev]}>{sev}</Badge>
                  <span className="text-xs text-muted-foreground">{items.length} incident{items.length > 1 ? "s" : ""}</span>
                </div>
                <div className="space-y-2">
                  {items.map((inc) => (
                    <IncidentRow
                      key={inc.id}
                      incident={inc}
                      onAcknowledge={() => updateMut.mutate({ id: inc.id, status: "acknowledged" })}
                      onResolve={(note) => updateMut.mutate({ id: inc.id, status: "resolved", note })}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="flex items-center justify-between rounded-lg border bg-white px-4 py-2 text-xs text-muted-foreground">
        <span>Page {data?.page ?? 1} of {Math.max(1, data?.pages ?? 1)}</span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={(data?.page ?? 1) <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>← Prev</Button>
          <Button variant="outline" size="sm" disabled={(data?.page ?? 1) >= (data?.pages ?? 1)} onClick={() => setPage((p) => p + 1)}>Next →</Button>
        </div>
      </div>
    </div>
  );
}

function groupBySeverity(items: Incident[]): Record<IncidentSeverity, Incident[]> {
  const out: Record<IncidentSeverity, Incident[]> = { critical: [], high: [], medium: [], low: [] };
  for (const i of items) out[i.severity].push(i);
  return out;
}

function IncidentRow({
  incident, onAcknowledge, onResolve,
}: {
  incident: Incident;
  onAcknowledge: () => void;
  onResolve: (note: string) => void;
}) {
  const evidence = safeParse(incident.evidence_json);
  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Badge variant={STATUS_VARIANT[incident.status]}>{incident.status}</Badge>
            <span className="font-mono text-xs text-muted-foreground">{incident.kind}</span>
            {incident.entity_type && (
              <span className="text-xs text-muted-foreground">
                · {incident.entity_type}{incident.entity_id ? `#${incident.entity_id}` : ""}
              </span>
            )}
          </div>
          <div className="mt-1 text-sm font-medium text-slate-900">{incident.title}</div>
          <div className="mt-1 text-sm text-slate-700">{incident.description}</div>
          {incident.suggested_action && (
            <div className="mt-2 text-xs text-muted-foreground">
              <span className="font-medium text-slate-700">Suggested:</span> {incident.suggested_action}
            </div>
          )}
          {Object.keys(evidence).length > 0 && (
            <div className="mt-2 rounded border bg-slate-50 p-2 text-[11px] text-slate-600 font-mono">
              {JSON.stringify(evidence)}
            </div>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <div className="text-xs text-muted-foreground tabular-nums">{new Date(incident.created_at).toLocaleString()}</div>
          {incident.status === "open" && (
            <Button size="sm" variant="outline" onClick={onAcknowledge}>
              <Check className="h-3.5 w-3.5" /> Acknowledge
            </Button>
          )}
          {incident.status !== "resolved" && (
            <ConfirmDialog
              title="Mark this incident resolved?"
              description="This action will be recorded in the audit trail. Provide an optional note."
              confirmLabel="Resolve"
              onConfirm={() => onResolve("resolved by operator")}
            >
              {(open) => (
                <Button size="sm" variant="outline" onClick={open}>
                  <X className="h-3.5 w-3.5" /> Resolve
                </Button>
              )}
            </ConfirmDialog>
          )}
          {incident.status === "resolved" && incident.resolved_at && (
            <div className="text-xs text-muted-foreground">Resolved {new Date(incident.resolved_at).toLocaleString()}</div>
          )}
        </div>
      </div>
    </div>
  );
}

function safeParse(s: string): Record<string, unknown> {
  try { return JSON.parse(s); } catch { return {}; }
}
