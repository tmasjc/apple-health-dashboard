import type { KpisResponse } from "../api/types";

interface Props {
  data: KpisResponse;
}

function KpiCell({ label, value, delta, format }: {
  label: string;
  value: number;
  delta: number;
  format?: (v: number) => string;
}) {
  const formatted = format ? format(value) : value.toFixed(0);
  return (
    <div className="kpi-cell">
      <div className="kpi-label">{label}</div>
      <div className="kpi-row">
        <span className="kpi-value">{formatted}</span>
        <span className="kpi-delta">
          {delta > 0 ? "+" : ""}
          {delta.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

export default function KpiCards({ data }: Props) {
  return (
    <div className="kpi-strip">
      <KpiCell
        label="Active kcal / day"
        value={data.active_kcal.value}
        delta={data.active_kcal.delta}
      />
      <KpiCell
        label="Exercise min / day"
        value={data.exercise_min.value}
        delta={data.exercise_min.delta}
      />
      <KpiCell
        label="Stand hrs / day"
        value={data.stand_hrs.value}
        delta={data.stand_hrs.delta}
        format={(v) => v.toFixed(1)}
      />
      <KpiCell
        label="Steps / day"
        value={data.steps.value}
        delta={data.steps.delta}
        format={(v) => v.toLocaleString("en-US", { maximumFractionDigits: 0 })}
      />
    </div>
  );
}
