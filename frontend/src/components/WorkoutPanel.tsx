import { useMemo, useState } from "react";
import Plot from "./Plot";
import type { WorkoutsResponse } from "../api/types";
import ChartCard from "./ChartCard";

interface Props {
  data: WorkoutsResponse;
}

export default function WorkoutPanel({ data }: Props) {
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const toggle = (name: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const filteredDonut = useMemo(() => {
    if (!data.donut) return null;
    const trace = { ...data.donut.traces[0] } as Record<string, unknown>;
    const labels = trace.labels as string[];
    const values = trace.values as number[];
    const marker = { ...(trace.marker as Record<string, unknown>) };
    const colors = marker.colors as string[];

    const keep = labels.map((l) => !hidden.has(l));
    trace.labels = labels.filter((_, i) => keep[i]);
    trace.values = values.filter((_, i) => keep[i]);
    marker.colors = colors.filter((_, i) => keep[i]);
    trace.marker = marker;

    return { traces: [trace], layout: data.donut.layout };
  }, [data.donut, hidden]);

  const filteredBar = useMemo(() => {
    if (!data.bar) return null;
    const traces = data.bar.traces
      .filter((t) => !hidden.has((t as Record<string, unknown>).name as string));
    return { traces, layout: data.bar.layout };
  }, [data.bar, hidden]);

  if (!data.donut && !data.bar) {
    return (
      <ChartCard title="Workouts" className="full-width">
        <div className="empty-msg">No workout data in selected range.</div>
      </ChartCard>
    );
  }

  return (
    <ChartCard title="Workouts" className="full-width">
      <div className="workout-inner">
        <div>
          {filteredDonut && (
            <Plot
              data={filteredDonut.traces as Plotly.Data[]}
              layout={{ ...filteredDonut.layout, height: 350, autosize: true } as Plotly.Layout}
              config={{ responsive: true, displayModeBar: false }}
              useResizeHandler
              style={{ width: "100%" }}
            />
          )}
        </div>
        <div>
          {filteredBar && (
            <Plot
              data={filteredBar.traces as Plotly.Data[]}
              layout={{ ...filteredBar.layout, height: 350, autosize: true } as Plotly.Layout}
              config={{ responsive: true, displayModeBar: false }}
              useResizeHandler
              style={{ width: "100%" }}
            />
          )}
        </div>
      </div>
      <div className="workout-legend">
        {data.types.map((t) => (
          <button
            key={t.name}
            className={`legend-chip ${hidden.has(t.name) ? "hidden" : ""}`}
            onClick={() => toggle(t.name)}
          >
            <span className="legend-dot" style={{ background: t.color }} />
            {t.name}
          </button>
        ))}
      </div>
    </ChartCard>
  );
}
