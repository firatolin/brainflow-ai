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
