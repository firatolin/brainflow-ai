import { useQuery } from "@tanstack/react-query";
import { settingsApi } from "@/api/endpoints";
import { useHealth } from "@/hooks/useHealth";
import { useAuth } from "@/hooks/useAuth";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export default function SettingsPage() {
  const settings = useQuery({ queryKey: ["app-settings"], queryFn: settingsApi.get, staleTime: 60_000 });
  const health = useHealth();
  const { state } = useAuth();

  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Read-only demo configuration · secrets live in backend .env</p>
      </div>

      <section className="rounded-lg border bg-white p-4">
        <h2 className="text-sm font-medium">Application</h2>
        {settings.isLoading ? (
          <Skeleton className="mt-3 h-16 w-full" />
        ) : settings.data ? (
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted-foreground">App name</dt>
            <dd>{settings.data.app_name}</dd>
            <dt className="text-muted-foreground">Environment</dt>
            <dd><Badge variant="muted">{settings.data.env}</Badge></dd>
            <dt className="text-muted-foreground">Auth mode</dt>
            <dd><Badge variant="info">{settings.data.auth_mode}</Badge></dd>
          </dl>
        ) : (
          <div className="text-sm text-red-700">Failed to load settings</div>
        )}
        {settings.data && (
          <p className="mt-3 rounded border bg-slate-50 p-2 text-xs text-muted-foreground">
            {settings.data.note}
          </p>
        )}
      </section>

      <section className="rounded-lg border bg-white p-4">
        <h2 className="text-sm font-medium">Admin account</h2>
        {settings.data ? (
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted-foreground">Username</dt>
            <dd className="font-mono text-xs">{settings.data.admin.username}</dd>
            <dt className="text-muted-foreground">Display name</dt>
            <dd>{settings.data.admin.display_name}</dd>
            <dt className="text-muted-foreground">Signed in as</dt>
            <dd>
              {state.status === "authenticated" ? (
                <Badge variant="success">{state.user.display_name}</Badge>
              ) : (
                <Badge variant="muted">Not signed in</Badge>
              )}
            </dd>
          </dl>
        ) : null}
      </section>

      <section className="rounded-lg border bg-white p-4">
        <h2 className="text-sm font-medium">System status</h2>
        {health.isLoading ? (
          <Skeleton className="mt-3 h-16 w-full" />
        ) : health.data ? (
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted-foreground">Backend</dt>
            <dd>
              <Badge variant={health.data.status === "ok" ? "success" : "danger"}>
                {health.data.status}
              </Badge>
            </dd>
            <dt className="text-muted-foreground">Database</dt>
            <dd>
              <Badge variant={health.data.database.ok ? "success" : "danger"}>
                {health.data.database.ok ? "ok" : "error"}
              </Badge>
            </dd>
            <dt className="text-muted-foreground">AI provider</dt>
            <dd>
              <Badge variant={health.data.ai.configured ? "info" : "muted"}>
                {health.data.ai.provider}{" "}
                {health.data.ai.configured ? "(configured)" : "(fallback)"}
              </Badge>
            </dd>
            <dt className="text-muted-foreground">Timestamp</dt>
            <dd className="text-xs text-muted-foreground">{new Date(health.data.timestamp).toLocaleString()}</dd>
          </dl>
        ) : (
          <div className="text-sm text-red-700">Backend unreachable</div>
        )}
      </section>

      <section className="rounded-lg border bg-white p-4">
        <h2 className="text-sm font-medium">External context</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Open-Meteo and Nager.Date are queried with a short timeout and cached. If they are unavailable, deterministic demo values are used instead.
        </p>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <div className="rounded border bg-slate-50 p-2">
            <div className="text-muted-foreground">Weather</div>
            <div className="mt-1"><WeatherProbe /></div>
          </div>
          <div className="rounded border bg-slate-50 p-2">
            <div className="text-muted-foreground">Holidays</div>
            <div className="mt-1"><HolidaysProbe /></div>
          </div>
        </div>
      </section>
    </div>
  );
}

function WeatherProbe() {
  const q = useQuery({
    queryKey: ["ctx-weather"],
    queryFn: () => fetch("/api/context/weather?zone=central").then((r) => r.json()),
    staleTime: 60_000,
  });
  if (q.isLoading) return <span className="text-muted-foreground">…</span>;
  if (q.isError || !q.data) return <Badge variant="danger">unreachable</Badge>;
  return <Badge variant={q.data.source === "open-meteo" ? "success" : "muted"}>{q.data.source}</Badge>;
}

function HolidaysProbe() {
  const q = useQuery({
    queryKey: ["ctx-holidays"],
    queryFn: () => fetch("/api/context/holidays?country=ET").then((r) => r.json()),
    staleTime: 60_000,
  });
  if (q.isLoading) return <span className="text-muted-foreground">…</span>;
  if (q.isError || !q.data) return <Badge variant="danger">unreachable</Badge>;
  const count = q.data.holidays?.length ?? 0;
  return <Badge variant={count > 0 ? "success" : "muted"}>{count} entries</Badge>;
}
