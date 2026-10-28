import { api } from "@/api/client";

export type DashboardSummary = {
  totals: {
    deliveries: number;
    active_deliveries: number;
    at_risk: number;
    critical_risk: number;
    delayed: number;
    delivered: number;
    completed: number;
  };
  on_time_rate_pct: number | null;
  estimated_delay_exposure_minutes: number;
  fleet: { total: number; active: number };
  incidents: { open: number; acknowledged: number };
  pending_approvals: number;
  recent_events: Array<{
    id: number;
    event_type: string;
    entity_type: string | null;
    entity_id: number | null;
    actor: string;
    created_at: string | null;
  }>;
  distributions: {
    status: Record<string, number>;
    risk: { low: number; medium: number; high: number; critical: number };
  };
  trend_7d: Array<{ date: string; created: number; delivered: number }>;
  generated_at: string;
};

export type AuthUser = {
  id: number;
  username: string;
  display_name: string;
};

export type AuthStatusResponse = {
  authenticated: boolean;
  user: AuthUser | null;
};

export type ScanRunResponse = {
  id: number;
  status: string;
  deliveries_scanned: number;
  incidents_created: number;
  incidents_reopened: number;
  incidents_auto_resolved: number;
};

export const endpoints = {
  dashboard: () => api.get<DashboardSummary>("/dashboard/summary"),
  login: (username: string, password: string) =>
    api.post<AuthUser>("/auth/login", { username, password }),
  logout: () => api.post<{ ok: boolean }>("/auth/logout"),
  authStatus: () => api.get<AuthStatusResponse>("/auth/status"),
  triggerScan: () => api.post<ScanRunResponse>("/incidents/scan"),
};
