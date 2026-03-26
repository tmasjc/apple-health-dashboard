import type { KpisResponse } from "../api/types";

interface Props {
  data: KpisResponse;
}

function KpiCard({ label, value, delta, format }: {
  label: string;
  value: number;
  delta: number;
  format?: (v: number) => string;
}) {
  const formatted = format ? format(value) : value.toFixed(0);
  const cls = delta > 0 ? "positive" : delta < 0 ? "negative" : "neutral";
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{formatted}</div>
      <div className={`kpi-delta ${cls}`}>
        {delta > 0 ? "+" : ""}
        {delta.toFixed(1)}%
      </div>
    </div>
  );
}

export default function KpiCards({ data }: Props) {
  return (
    <div className="kpi-grid">
      <KpiCard
        label="Avg Active kcal / day"
        value={data.active_kcal.value}
        delta={data.active_kcal.delta}
      />
      <KpiCard
        label="Avg Exercise min / day"
        value={data.exercise_min.value}
        delta={data.exercise_min.delta}
      />
      <KpiCard
        label="Avg Stand hrs / day"
        value={data.stand_hrs.value}
        delta={data.stand_hrs.delta}
        format={(v) => v.toFixed(1)}
      />
      <KpiCard
        label="Avg Steps / day"
        value={data.steps.value}
        delta={data.steps.delta}
        format={(v) => v.toLocaleString("en-US", { maximumFractionDigits: 0 })}
      />
    </div>
  );
}
