import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, X, Play, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { actionsApi, type OperationalAction, type ActionPage } from "@/api/endpoints";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

type Status = NonNullable<ActionPage["items"][number]["status"]>;

const STATUS_VARIANT: Record<Status, "muted" | "warning" | "info" | "success" | "danger"> = {
  draft: "muted",
  pending_approval: "warning",
  approved: "info",
  executed: "success",
  rejected: "danger",
  cancelled: "muted",
};

export default function ApprovalsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("pending_approval");
  const qc = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["actions", statusFilter],
    queryFn: () => actionsApi.list({ page_size: 50, status: statusFilter || undefined }),
  });

  const approveMut = useMutation({
    mutationFn: (id: number) => actionsApi.approve(id),
    onSuccess: () => {
      toast.success("Approved");
      qc.invalidateQueries({ queryKey: ["actions"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Approve failed"),
  });

  const rejectMut = useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) => actionsApi.reject(id, undefined, note),
    onSuccess: () => {
      toast.success("Rejected");
      qc.invalidateQueries({ queryKey: ["actions"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Reject failed"),
  });

  const executeMut = useMutation({
    mutationFn: (id: number) => actionsApi.execute(id),
    onSuccess: (action) => {
      toast.success("Executed", { description: `Applied ${extractApplied(action)}` });
      qc.invalidateQueries({ queryKey: ["actions"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
      qc.invalidateQueries({ queryKey: ["deliveries"] });
    },
    onError: (e) => {
      if (e instanceof ApiError && e.status === 409 && typeof e.detail === "object") {
        const detail = e.detail as { detail?: { message?: string; reasons?: string[] } };
        const reasons = detail.detail?.reasons?.join(" · ") ?? e.message;
        toast.error(`Blocked: ${reasons}`, { duration: 8000 });
      } else {
        toast.error(e instanceof Error ? e.message : "Execute failed");
      }
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Approvals</h1>
          <p className="text-sm text-muted-foreground">
            Human review required before any operational change is applied
          </p>
        </div>
        <Select value={statusFilter || "all"} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-52"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="pending_approval">Pending approval</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="executed">Executed</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)}</div>
      ) : isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Failed to load: {error instanceof Error ? error.message : "unknown"}
        </div>
      ) : (data?.items.length ?? 0) === 0 ? (
        <div className="rounded-lg border bg-white p-8 text-center text-sm text-muted-foreground">
          No actions in this state.
        </div>
      ) : (
        <div className="space-y-2">
          {data!.items.map((a) => (
            <ActionCard
              key={a.id}
              action={a}
              onApprove={() => approveMut.mutate(a.id)}
              onReject={(note) => rejectMut.mutate({ id: a.id, note })}
              onExecute={() => executeMut.mutate(a.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ActionCard({
  action, onApprove, onReject, onExecute,
}: {
  action: OperationalAction;
  onApprove: () => void;
  onReject: (note: string) => void;
  onExecute: () => void;
}) {
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectNote, setRejectNote] = useState("");

  const status = action.status as Status;

  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Badge variant={STATUS_VARIANT[status]}>{status}</Badge>
            <span className="text-xs text-muted-foreground">
              #{action.id} · plan #{action.plan_id ?? "—"} · {action.action_type}
            </span>
          </div>
          <div className="mt-1 text-sm font-medium text-slate-900">{action.reason}</div>
          <div className="mt-1 text-xs text-muted-foreground">{action.expected_impact}</div>
          <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
            <span>requested {new Date(action.requested_at).toLocaleString()}</span>
            {action.reviewer && <span>reviewer: <span className="text-slate-700">{action.reviewer}</span></span>}
            {action.executed_at && <span>executed {new Date(action.executed_at).toLocaleString()}</span>}
          </div>
          {action.execution_result && (
            <div className="mt-2 rounded border bg-slate-50 p-2 text-[11px] font-mono text-slate-600">
              {action.execution_result}
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-col items-end gap-2">
          {status === "pending_approval" && (
            <>
              <Button size="sm" onClick={onApprove}>
                <Check className="h-3.5 w-3.5" /> Approve
              </Button>
              <Button size="sm" variant="outline" onClick={() => setRejectOpen(true)}>
                <X className="h-3.5 w-3.5" /> Reject
              </Button>
            </>
          )}
          {status === "approved" && (
            <Button size="sm" onClick={onExecute}>
              <Play className="h-3.5 w-3.5" /> Execute
            </Button>
          )}
          {status === "rejected" && (
            <div className="flex items-center gap-1 text-xs text-red-700">
              <AlertCircle className="h-3 w-3" /> Rejected
            </div>
          )}
        </div>
      </div>

      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Reject action #{action.id}?</DialogTitle>
            <DialogDescription>Rejections are recorded in the audit trail.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="note">Note (optional)</Label>
            <Input id="note" value={rejectNote} onChange={(e) => setRejectNote(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={() => { onReject(rejectNote); setRejectOpen(false); }}>
              Reject
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function extractApplied(a: OperationalAction): string {
  if (!a.execution_result) return "no changes";
  try {
    const r = JSON.parse(a.execution_result) as { applied_changes?: number };
    return `${r.applied_changes ?? 0} changes`;
  } catch {
    return "changes applied";
  }
}
