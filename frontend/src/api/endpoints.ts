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

// ===== Deliveries =====
export type DeliveryStatus =
  | "pending" | "assigned" | "in_transit" | "delayed"
  | "delivered" | "failed" | "cancelled";
export type DeliveryPriority = "low" | "normal" | "high" | "urgent";

export type Delivery = {
  id: number;
  tracking_number: string;
  customer_ref: string;
  origin: string;
  destination: string;
  scheduled_dispatch: string;
  promised_deadline: string;
  estimated_arrival: string | null;
  actual_arrival: string | null;
  priority: DeliveryPriority;
  status: DeliveryStatus;
  vehicle_id: number | null;
  distance_km: number;
  cost_estimate: number;
  weather_exposure: number;
  risk_score: number;
  risk_explanation: string | null;
  created_at: string;
  updated_at: string;
};

export type DeliveryPage = {
  items: Delivery[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type DeliveryHistory = {
  id: number;
  delivery_id: number;
  event_type: string;
  from_status: string | null;
  to_status: string | null;
  from_vehicle_id: number | null;
  to_vehicle_id: number | null;
  note: string | null;
  created_at: string;
};

export type DeliveryCreateInput = {
  tracking_number: string;
  customer_ref: string;
  origin: string;
  destination: string;
  scheduled_dispatch: string;
  promised_deadline: string;
  priority: DeliveryPriority;
  distance_km: number;
  cost_estimate: number;
  weather_exposure: number;
  vehicle_id?: number | null;
};

// ===== Vehicles =====
export type VehicleStatus = "available" | "on_route" | "maintenance" | "out_of_service";
export type VehicleType = "van" | "truck" | "motorbike" | "car";

export type Vehicle = {
  id: number;
  code: string;
  vehicle_type: VehicleType;
  capacity: number;
  status: VehicleStatus;
  location_zone: string;
  available: boolean;
  cost_per_km: number;
  created_at: string;
  updated_at: string;
};

export type VehiclePage = {
  items: Vehicle[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type VehicleCreateInput = {
  code: string;
  vehicle_type: VehicleType;
  capacity: number;
  status: VehicleStatus;
  location_zone: string;
  available: boolean;
  cost_per_km: number;
};

export type VehicleUpdateInput = Partial<Omit<VehicleCreateInput, "code">>;

function buildQuery(params: Record<string, string | number | boolean | undefined | null>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export const deliveriesApi = {
  list: (params: {
    page?: number; page_size?: number;
    status?: string; priority?: string;
    vehicle_id?: number; q?: string;
    sort?: string; order?: "asc" | "desc";
  }) => api.get<DeliveryPage>(`/deliveries${buildQuery(params)}`),
  get: (id: number) => api.get<Delivery>(`/deliveries/${id}`),
  history: (id: number) => api.get<DeliveryHistory[]>(`/deliveries/${id}/history`),
  create: (input: DeliveryCreateInput) => api.post<Delivery>("/deliveries", input),
  patch: (id: number, input: Partial<DeliveryCreateInput>) =>
    api.patch<Delivery>(`/deliveries/${id}`, input),
  assign: (id: number, vehicle_id: number | null) =>
    api.post<Delivery>(`/deliveries/${id}/assign`, { vehicle_id }),
  status: (id: number, status: DeliveryStatus, note?: string) =>
    api.post<Delivery>(`/deliveries/${id}/status`, { status, note }),
};

export const vehiclesApi = {
  list: (params: {
    page?: number; page_size?: number;
    status?: string; available?: boolean; q?: string;
  }) => api.get<VehiclePage>(`/vehicles${buildQuery(params)}`),
  get: (id: number) => api.get<Vehicle>(`/vehicles/${id}`),
  create: (input: VehicleCreateInput) => api.post<Vehicle>("/vehicles", input),
  patch: (id: number, input: VehicleUpdateInput) =>
    api.patch<Vehicle>(`/vehicles/${id}`, input),
};

// ===== Customer drafts =====
export type CustomerDraft = {
  delivery_id: number;
  tracking_number: string;
  recipient_category: string;
  reason: string;
  body: string;
  source: "llm" | "template";
  facts: Record<string, unknown>;
  reviewed: boolean;
  status: string;
  requires_human_review: boolean;
};

export const customerDraftsApi = {
  get: (id: number) => api.get<CustomerDraft>(`/customer-drafts/${id}`),
};

// ===== Incidents =====
export type IncidentSeverity = "low" | "medium" | "high" | "critical";
export type IncidentStatus = "open" | "acknowledged" | "resolved";

export type Incident = {
  id: number;
  kind: string;
  entity_type: string;
  entity_id: number | null;
  discriminator: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  title: string;
  description: string;
  evidence_json: string;
  suggested_action: string;
  created_at: string;
  updated_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  resolution_note: string | null;
};

export type IncidentPage = {
  items: Incident[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export const incidentsApi = {
  list: (params: {
    page?: number; page_size?: number;
    status?: string; severity?: string;
    kind?: string; entity_type?: string;
    sort?: string; order?: "asc" | "desc";
  }) => api.get<IncidentPage>(`/incidents${buildQuery(params)}`),
  scan: () => api.post<ScanRunResponse>("/incidents/scan"),
  update: (id: number, payload: { status: IncidentStatus; resolution_note?: string | null }) =>
    api.patch<Incident>(`/incidents/${id}`, payload),
};

// ===== Plans =====
export type PlanKind = "baseline" | "minimize_delays" | "balanced";
export type PlanStatus = "draft" | "submitted" | "approved" | "rejected" | "executed" | "cancelled";

export type PlanItem = {
  id: number;
  delivery_id: number;
  from_vehicle_id: number | null;
  to_vehicle_id: number | null;
  sequence_position: number;
  expected_delay_minutes: number;
  expected_late: boolean;
};

export type RecoveryPlan = {
  id: number;
  kind: PlanKind;
  status: PlanStatus;
  expected_late_count: number;
  expected_total_delay_minutes: number;
  expected_priority_weighted_delay: number;
  expected_cost: number;
  expected_additional_travel_km: number;
  changes_count: number;
  feasible: boolean;
  infeasibility_reasons_json: string;
  explanation: string;
  created_at: string;
  items: PlanItem[];
};

export type PlanPage = {
  items: RecoveryPlan[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type OperationalAction = {
  id: number;
  action_type: string;
  plan_id: number | null;
  status: "draft" | "pending_approval" | "approved" | "rejected" | "executed" | "cancelled";
  before_state_json: string;
  proposed_state_json: string;
  expected_impact: string;
  reason: string;
  requested_at: string;
  decided_at: string | null;
  executed_at: string | null;
  reviewer: string | null;
  execution_result: string | null;
};

export const plansApi = {
  generate: () => api.post<RecoveryPlan[]>("/plans/generate"),
  list: (params: { page?: number; page_size?: number; kind?: string; status?: string }) =>
    api.get<PlanPage>(`/plans${buildQuery(params)}`),
  get: (id: number) => api.get<RecoveryPlan>(`/plans/${id}`),
  submit: (id: number, actor?: string) =>
    api.post<OperationalAction>(`/plans/${id}/submit`, { actor: actor ?? null }),
};

// ===== Actions (approvals) =====
export type ActionPage = {
  items: OperationalAction[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export const actionsApi = {
  list: (params: { page?: number; page_size?: number; status?: string }) =>
    api.get<ActionPage>(`/actions${buildQuery(params)}`),
  get: (id: number) => api.get<OperationalAction>(`/actions/${id}`),
  approve: (id: number, reviewer?: string, note?: string) =>
    api.post<OperationalAction>(`/actions/${id}/approve`, { reviewer: reviewer ?? null, note: note ?? null }),
  reject: (id: number, reviewer?: string, note?: string) =>
    api.post<OperationalAction>(`/actions/${id}/reject`, { reviewer: reviewer ?? null, note: note ?? null }),
  execute: (id: number, reviewer?: string) =>
    api.post<OperationalAction>(`/actions/${id}/execute`, { reviewer: reviewer ?? null }),
};

// ===== Simulations =====
export type SimulationScenario =
  | "vehicle_unavailable" | "heavy_rain" | "urgent_added"
  | "capacity_change" | "deadline_earlier" | "assignment_failed";

export type Simulation = {
  id: number;
  scenario: SimulationScenario;
  params_json: string;
  baseline_metrics_json: string;
  simulated_metrics_json: string;
  diff_json: string;
  explanation: string;
  created_at: string;
};

export const simulationsApi = {
  create: (scenario: SimulationScenario, params: Record<string, unknown>) =>
    api.post<Simulation>("/simulations", { scenario, params }),
  get: (id: number) => api.get<Simulation>(`/simulations/${id}`),
};
