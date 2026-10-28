import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DeliveriesPage from "@/pages/deliveries/DeliveriesPage";
import { AuthProvider } from "@/hooks/useAuth";

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/deliveries"]}>
        <AuthProvider>
          <DeliveriesPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const samplePage = {
  items: [
    {
      id: 1, tracking_number: "BF-TEST-1", customer_ref: "cust", origin: "A",
      destination: "Gerji Yard", scheduled_dispatch: "2026-10-28T08:00:00Z",
      promised_deadline: "2026-10-28T12:00:00Z", estimated_arrival: null,
      actual_arrival: null, priority: "urgent", status: "assigned",
      vehicle_id: 1, distance_km: 10, cost_estimate: 20, weather_exposure: 0.2,
      risk_score: 35, risk_explanation: null,
      created_at: "2026-10-28T07:00:00Z", updated_at: "2026-10-28T07:00:00Z",
    },
  ],
  total: 1, page: 1, page_size: 20, pages: 1,
};

describe("DeliveriesPage", () => {
  beforeEach(() => {
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/auth/status")) {
        return new Response(
          JSON.stringify({ authenticated: true, user: { id: 1, username: "admin", display_name: "Admin" } }),
          { status: 200 },
        );
      }
      if (url.includes("/api/vehicles")) {
        return new Response(
          JSON.stringify({ items: [{ id: 1, code: "VAN-01" }], total: 1, page: 1, page_size: 100, pages: 1 }),
          { status: 200 },
        );
      }
      if (url.includes("/api/deliveries")) {
        return new Response(JSON.stringify(samplePage), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    }) as unknown as typeof fetch;
  });

  it("renders deliveries table with data", async () => {
    wrap();
    expect(await screen.findByText("BF-TEST-1")).toBeInTheDocument();
    expect(screen.getByText("Gerji Yard")).toBeInTheDocument();
    expect(screen.getAllByText("Urgent").length).toBeGreaterThan(0);
  });

  it("shows total count", async () => {
    wrap();
    await waitFor(() => {
      expect(screen.getByText(/1 total/)).toBeInTheDocument();
    });
  });
});
