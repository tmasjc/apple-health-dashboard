import Plot from "./Plot";
import type { PlotData } from "../api/types";

interface Props {
  data: PlotData;
  height?: number;
}

export default function PlotlyChart({ data, height }: Props) {
  if (!data.traces || data.traces.length === 0) {
    return <div className="empty-msg">No data available</div>;
  }

  const h = height ?? (data.layout?.height as number | undefined) ?? 300;

  return (
    <Plot
      data={data.traces as Plotly.Data[]}
      layout={{
        ...data.layout,
        height: h,
        autosize: true,
      } as Plotly.Layout}
      config={{ responsive: true, displayModeBar: false }}
      useResizeHandler
      style={{ width: "100%" }}
    />
  );
}
