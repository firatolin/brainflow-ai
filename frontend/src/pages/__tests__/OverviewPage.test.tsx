import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import OverviewPage from "@/pages/OverviewPage";

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("OverviewPage", () => {
  beforeEach(() => {
    global.fetch = vi.fn(async () =>
      new Response(
        JSON.stringify({
          totals: {
            deliveries: 43, active_deliveries: 40, at_risk: 4, critical_risk: 1,
            delayed: 2, delivered: 3, completed: 3,
          },
          on_time_rate_pct: 87.5,
          estimated_delay_exposure_minutes: 120,
          fleet: { total: 6, active: 5 },
          incidents: { open: 3, acknowledged: 1 },
          pending_approvals: 2,
          recent_events: [
            { id: 1, event_type: "action.approved", entity_type: "operational_action",
              entity_id: 1, actor: "Admin", created_at: new Date().toISOString() },
          ],
          distributions: {
            status: { pending: 30, assigned: 10, delivered: 3 },
            risk: { low: 36, medium: 3, high: 1, critical: 0 },
          },
          trend_7d: [
            { date: "2026-10-22", created: 0, delivered: 0 },
            { date: "2026-10-23", created: 0, delivered: 0 },
            { date: "2026-10-24", created: 0, delivered: 0 },
            { date: "2026-10-25", created: 0, delivered: 0 },
            { date: "2026-10-26", created: 0, delivered: 0 },
            { date: "2026-10-27", created: 0, delivered: 0 },
            { date: "2026-10-28", created: 43, delivered: 3 },
          ],
          generated_at: new Date().toISOString(),
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    ) as unknown as typeof fetch;
  });

  it("renders KPI numbers from dashboard data", async () => {
    wrap();
    expect(await screen.findByText("Operations overview")).toBeInTheDocument();
    await waitFor(() => {
      // Active deliveries value = 40 (KPI card value element)
      const cardValue = screen.getAllByText("40", { selector: ".text-2xl" });
      expect(cardValue.length).toBeGreaterThan(0);
      // On-time rate is rendered as integer percent
      expect(screen.getByText("88%")).toBeInTheDocument();
    });
  });

  it("renders recent activity row", async () => {
    wrap();
    expect(await screen.findByText(/action.approved/)).toBeInTheDocument();
  });
});
