import { useQuery } from "@tanstack/react-query";
import { endpoints } from "@/api/endpoints";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: endpoints.dashboard,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}
