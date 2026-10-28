import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";
import { AuthProvider } from "@/hooks/useAuth";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

function renderLogin() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/auth/status")) {
        return new Response(JSON.stringify({ authenticated: false, user: null }), { status: 200 });
      }
      if (url.includes("/api/auth/login")) {
        return new Response(
          JSON.stringify({ id: 1, username: "admin", display_name: "Admin" }),
          { status: 200 },
        );
      }
      return new Response("{}", { status: 404 });
    }) as unknown as typeof fetch;
  });

  it("renders form fields", async () => {
    renderLogin();
    expect(await screen.findByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows validation errors when submitting empty", async () => {
    renderLogin();
    const submit = await screen.findByRole("button", { name: /sign in/i });
    await userEvent.click(submit);
    await waitFor(() => {
      expect(screen.getByText(/username is required/i)).toBeInTheDocument();
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  it("submits with credentials and calls login API", async () => {
    renderLogin();
    await userEvent.type(await screen.findByLabelText(/username/i), "admin");
    await userEvent.type(screen.getByLabelText(/password/i), "BrainFlow@2026");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      const calls = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls;
      const loginCall = calls.find((c) => String(c[0]).includes("/api/auth/login"));
      expect(loginCall).toBeTruthy();
    });
  });
});
