import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { auditApi } from "@/api/endpoints";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

const COMMON_TYPES = [
  "action.submitted",
  "action.approved",
  "action.rejected",
  "action.executed",
  "delivery.reassigned",
  "incident.created",
  "incident.resolved",
  "plan.generated",
];

export default function AuditPage() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [eventType, setEventType] = useState("");

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["audit", page, q, eventType],
    queryFn: () =>
      auditApi.list({
        page,
        page_size: 50,
        q: q || undefined,
        event_type: eventType || undefined,
      }),
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Audit history</h1>
        <p className="text-sm text-muted-foreground">
          Append-only log · {data?.total ?? 0} events
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-64">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search actor or context"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
            className="pl-8"
          />
        </div>
        <Select value={eventType || "all"} onValueChange={(v) => { setEventType(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-56"><SelectValue placeholder="Event type" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {COMMON_TYPES.map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border bg-white">
        {isLoading ? (
          <div className="p-4 space-y-2">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
        ) : isError ? (
          <div className="p-4 text-sm text-red-700">
            Failed to load: {error instanceof Error ? error.message : "unknown"}
          </div>
        ) : (data?.items.length ?? 0) === 0 ? (
          <div className="p-8 text-center text-sm text-muted-foreground">
            No audit events match the filters.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50/60 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-2 font-medium">Time</th>
                <th className="px-4 py-2 font-medium">Event</th>
                <th className="px-4 py-2 font-medium">Entity</th>
                <th className="px-4 py-2 font-medium">Actor</th>
                <th className="px-4 py-2 font-medium">Context</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((e) => (
                <tr key={e.id} className="border-b last:border-b-0">
                  <td className="px-4 py-1.5 text-xs tabular-nums text-muted-foreground whitespace-nowrap">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-1.5">
                    <Badge variant="info">{e.event_type}</Badge>
                  </td>
                  <td className="px-4 py-1.5 text-xs text-slate-700">
                    {e.entity_type ?? "—"}
                    {e.entity_id !== null ? ` #${e.entity_id}` : ""}
                  </td>
                  <td className="px-4 py-1.5 text-xs">{e.actor}</td>
                  <td className="px-4 py-1.5 text-[11px] font-mono text-slate-600 max-w-md truncate">
                    {e.context_json}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="flex items-center justify-between border-t px-4 py-2 text-xs text-muted-foreground">
          <span>Page {data?.page ?? 1} of {Math.max(1, data?.pages ?? 1)}</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={(data?.page ?? 1) <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>← Prev</Button>
            <Button variant="outline" size="sm" disabled={(data?.page ?? 1) >= (data?.pages ?? 1)} onClick={() => setPage((p) => p + 1)}>Next →</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
