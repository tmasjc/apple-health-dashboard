import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "../api/client";
import type { KpisResponse, Meta, PlotData, WorkoutsResponse } from "../api/types";

function dateParams(start: string, end: string) {
  return { start, end };
}

export function useMeta() {
  return useQuery({
    queryKey: ["meta"],
    queryFn: () => fetchApi<Meta>("/meta"),
    staleTime: Infinity,
  });
}

export function useKpis(start: string, end: string) {
  return useQuery({
    queryKey: ["kpis", start, end],
    queryFn: () => fetchApi<KpisResponse>("/kpis", dateParams(start, end)),
    staleTime: Infinity,
    enabled: !!start && !!end,
  });
}

export function useWorkouts(start: string, end: string) {
  return useQuery({
    queryKey: ["workouts", start, end],
    queryFn: () => fetchApi<WorkoutsResponse>("/workouts", dateParams(start, end)),
    staleTime: Infinity,
    enabled: !!start && !!end,
  });
}

export function usePlotEndpoint(key: string, start: string, end: string) {
  return useQuery({
    queryKey: [key, start, end],
    queryFn: () => fetchApi<PlotData>(`/${key}`, dateParams(start, end)),
    staleTime: Infinity,
    enabled: !!start && !!end,
  });
}
