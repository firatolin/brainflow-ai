import { Badge } from "@/components/ui/badge";
import type { DeliveryStatus, DeliveryPriority } from "@/api/endpoints";

type BadgeVariant = "default" | "secondary" | "muted" | "info" | "warning" | "danger" | "success" | "destructive" | "outline";

const STATUS_VARIANT: Record<DeliveryStatus, BadgeVariant> = {
  pending: "muted",
  assigned: "info",
  in_transit: "info",
  delayed: "warning",
  delivered: "success",
  failed: "danger",
  cancelled: "muted",
};

const STATUS_LABEL: Record<DeliveryStatus, string> = {
  pending: "Pending",
  assigned: "Assigned",
  in_transit: "In transit",
  delayed: "Delayed",
  delivered: "Delivered",
  failed: "Failed",
  cancelled: "Cancelled",
};

const PRIORITY_VARIANT: Record<DeliveryPriority, BadgeVariant> = {
  low: "muted",
  normal: "secondary",
  high: "warning",
  urgent: "danger",
};

export function DeliveryStatusBadge({ status }: { status: DeliveryStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>;
}

export function DeliveryPriorityBadge({ priority }: { priority: DeliveryPriority }) {
  return <Badge variant={PRIORITY_VARIANT[priority]}>{priority.charAt(0).toUpperCase() + priority.slice(1)}</Badge>;
}

export function RiskScoreBadge({ score }: { score: number }) {
  if (score < 25) return <Badge variant="muted">{score.toFixed(0)}</Badge>;
  if (score < 50) return <Badge variant="info">{score.toFixed(0)}</Badge>;
  if (score < 75) return <Badge variant="warning">{score.toFixed(0)}</Badge>;
  return <Badge variant="danger">{score.toFixed(0)}</Badge>;
}

export function AvailableBadge({ available }: { available: boolean }) {
  return available ? <Badge variant="success">Available</Badge> : <Badge variant="muted">Unavailable</Badge>;
}
