export interface Profile {
  display_name: string;
  gender: "male" | "female";
}

export interface Meta {
  min_date: string;
  max_date: string;
  profile: Profile;
}

export interface KpiItem {
  value: number;
  delta: number;
}

export interface KpisResponse {
  active_kcal: KpiItem;
  exercise_min: KpiItem;
  stand_hrs: KpiItem;
  steps: KpiItem;
}

export interface PlotData {
  traces: Record<string, unknown>[];
  layout: Record<string, unknown>;
}

export interface WorkoutType {
  name: string;
  color: string;
}

export interface WorkoutsResponse {
  donut: PlotData | null;
  bar: PlotData | null;
  types: WorkoutType[];
}
