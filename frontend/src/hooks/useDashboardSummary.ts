import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { monthIso } from "@/lib/format";
import type { DashboardSummary, GamingEarningsSummary } from "@/lib/types";

// Moved out of pages/Dashboard.tsx so other pages (Budget) can depend on it
// without statically pulling the whole Dashboard page into their bundle chunk.
export function useSummary() {
  return useQuery({ queryKey: ["dashboard"], queryFn: () => apiGet<DashboardSummary>("/dashboard/summary"), retry: false });
}

export function useGamingEarnings() {
  return useQuery({
    queryKey: ["gaming", "earnings", monthIso()],
    queryFn: () => apiGet<GamingEarningsSummary>(`/gaming/earnings?month=${monthIso()}`),
    retry: false,
    staleTime: 60_000,
  });
}
