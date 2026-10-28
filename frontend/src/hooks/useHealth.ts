import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export type Health = {
  status: "ok" | "degraded";
  app: string;
  env: string;
  database: { ok: boolean; error: string | null };
  ai: { provider: string; configured: boolean };
  timestamp: string;
};

export function useHealth() {
  return useQuery<Health>({
    queryKey: ["health"],
    queryFn: () => api.get<Health>("/health"),
    refetchInterval: 30_000,
  });
}
