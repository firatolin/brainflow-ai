import { formatDistanceToNow, parseISO } from "date-fns";

type Event = {
  id: number;
  event_type: string;
  entity_type: string | null;
  entity_id: number | null;
  actor: string;
  created_at: string | null;
};

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true });
  } catch {
    return iso;
  }
}

export function RecentEvents({ events }: { events: Event[] }) {
  if (events.length === 0) {
    return (
      <div className="text-xs text-muted-foreground">
        No events yet. Run a scan or create a plan to populate the log.
      </div>
    );
  }
  return (
    <ul className="divide-y">
      {events.map((e) => (
        <li key={e.id} className="flex items-start justify-between gap-3 py-2.5">
          <div className="min-w-0">
            <div className="truncate text-sm text-slate-800">
              <span className="font-medium">{e.event_type}</span>
              {e.entity_type && (
                <span className="text-muted-foreground">
                  {" "}
                  · {e.entity_type}
                  {e.entity_id !== null ? `#${e.entity_id}` : ""}
                </span>
              )}
            </div>
            <div className="text-xs text-muted-foreground">
              by <span className="text-slate-700">{e.actor}</span>
            </div>
          </div>
          <div className="shrink-0 text-xs text-muted-foreground tabular-nums">
            {fmtTime(e.created_at)}
          </div>
        </li>
      ))}
    </ul>
  );
}
