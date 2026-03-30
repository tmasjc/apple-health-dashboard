import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchApi, postApi } from "../api/client";
import type { KpisResponse, Meta, PlotData, Profile, WorkoutsResponse } from "../api/types";

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

export function usePlotEndpoint(
  key: string,
  start: string,
  end: string,
  extraParams?: Record<string, string>,
) {
  const params = { ...dateParams(start, end), ...extraParams };
  return useQuery({
    queryKey: [key, start, end, extraParams],
    queryFn: () => fetchApi<PlotData>(`/${key}`, params),
    staleTime: Infinity,
    enabled: !!start && !!end,
  });
}

export function useSaveProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (profile: Profile) => postApi<Profile>("/profile", profile),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["meta"] }),
  });
}
