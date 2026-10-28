import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Package, Truck, AlertTriangle, Route as RouteIcon,
  FlaskConical, Bot, BarChart3, CheckSquare, History, Settings as SettingsIcon,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useHealth } from "@/hooks/useHealth";
import { useAuth } from "@/hooks/useAuth";

type NavItem = { to: string; label: string; icon: React.ComponentType<{ className?: string }> };

const NAV: NavItem[] = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/deliveries", label: "Deliveries", icon: Package },
  { to: "/fleet", label: "Fleet", icon: Truck },
  { to: "/exceptions", label: "Exceptions", icon: AlertTriangle },
  { to: "/recovery", label: "Recovery Planning", icon: RouteIcon },
  { to: "/simulations", label: "Simulations", icon: FlaskConical },
  { to: "/copilot", label: "AI Copilot", icon: Bot },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/approvals", label: "Approvals", icon: CheckSquare },
  { to: "/audit", label: "Audit History", icon: History },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

function Sidebar() {
  return (
    <aside className="hidden md:flex md:w-60 md:flex-col border-r bg-slate-50/50">
      <div className="px-4 py-5 border-b">
        <div className="text-base font-semibold tracking-tight">BrainFlow AI</div>
        <div className="text-xs text-muted-foreground">Logistics operations</div>
      </div>
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground/80 hover:bg-slate-200/60",
              )
            }
          >
            <item.icon className="h-4 w-4" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

function Topbar() {
  const health = useHealth();
  const { state, logout } = useAuth();
  const navigate = useNavigate();

  const aiConfigured = health.data?.ai?.configured ?? false;
  const provider = health.data?.ai?.provider ?? "unknown";
  const healthy = health.data?.status === "ok";

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="flex items-center justify-between border-b bg-white px-6 py-3">
      <div className="flex items-center gap-3">
        <div className="text-sm font-medium">Operations</div>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs",
            healthy
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-red-200 bg-red-50 text-red-700",
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", healthy ? "bg-emerald-500" : "bg-red-500")} />
          {healthy ? "Healthy" : "Degraded"}
        </span>
        <span className="text-xs text-muted-foreground">
          AI: {provider} {aiConfigured ? "(configured)" : "(fallback)"}
        </span>
      </div>
      <div className="flex items-center gap-3">
        {state.status === "authenticated" && (
          <>
            <div className="text-xs text-muted-foreground">
              Signed in as <span className="text-slate-800 font-medium">{state.user.display_name}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={onLogout}>
              <LogOut className="h-4 w-4" />
              Sign out
            </Button>
          </>
        )}
      </div>
    </header>
  );
}

export function AppLayout() {
  return (
    <div className="flex h-screen bg-white">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-auto bg-slate-50/30 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
