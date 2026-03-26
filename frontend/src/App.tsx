import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import DateRangeSlider from "./components/DateRangeSlider";
import KpiCards from "./components/KpiCards";
import ChartCard from "./components/ChartCard";
import PlotlyChart from "./components/PlotlyChart";
import WorkoutPanel from "./components/WorkoutPanel";
import {
  useKpis,
  useMeta,
  usePlotEndpoint,
  useWorkouts,
} from "./hooks/useHealthData";

const queryClient = new QueryClient();

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function Dashboard() {
  const { data: meta, isLoading: metaLoading } = useMeta();

  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  const effectiveStart = start || (meta ? addDays(meta.max_date, -180) : "");
  const effectiveEnd = end || meta?.max_date || "";

  const handleDateChange = useCallback((s: string, e: string) => {
    setStart(s);
    setEnd(e);
  }, []);

  const { data: kpis } = useKpis(effectiveStart, effectiveEnd);
  const { data: workoutsData } = useWorkouts(effectiveStart, effectiveEnd);
  const { data: vo2 } = usePlotEndpoint("vo2", effectiveStart, effectiveEnd);
  const { data: rhrHrv } = usePlotEndpoint("rhr-hrv", effectiveStart, effectiveEnd);
  const { data: sleepStages } = usePlotEndpoint("sleep-stages", effectiveStart, effectiveEnd);
  const { data: sleepDuration } = usePlotEndpoint("sleep-duration", effectiveStart, effectiveEnd);
  const { data: sleepConsistency } = usePlotEndpoint("sleep-consistency", effectiveStart, effectiveEnd);
  const { data: wristTemp } = usePlotEndpoint("wrist-temp", effectiveStart, effectiveEnd);

  if (metaLoading || !meta) {
    return <div className="dashboard"><div className="chart-loading">Loading...</div></div>;
  }

  return (
    <div className="dashboard">
      {/* Header */}
      <div className="header">
        <div className="header-left">
          <h1 className="page-title">Hello Thomas</h1>
          <div className="nav-pills">
            <a href="#overview" className="nav-pill">📊 Overview</a>
            <a href="#fitness" className="nav-pill">💪 Fitness</a>
            <a href="#heart" className="nav-pill">❤️ Heart</a>
            <a href="#sleep" className="nav-pill">😴 Sleep</a>
          </div>
        </div>
        <div className="header-right">
          <DateRangeSlider
            minDate={meta.min_date}
            maxDate={meta.max_date}
            onChange={handleDateChange}
          />
        </div>
      </div>

      {/* Overview */}
      <div id="overview" className="section-header">Overview</div>
      <p className="section-desc">
        % change compares the selected range against the preceding period of equal length.
      </p>
      {kpis ? <KpiCards data={kpis} /> : <div className="chart-loading">Loading...</div>}

      {/* Fitness */}
      <div id="fitness" className="section-header">Fitness</div>
      <div className="grid-2col">
        {workoutsData ? (
          <WorkoutPanel data={workoutsData} />
        ) : (
          <ChartCard title="Workouts" className="full-width">
            <div className="chart-loading">Loading...</div>
          </ChartCard>
        )}
      </div>

      {/* Heart */}
      <div id="heart" className="section-header">Heart</div>
      <div className="grid-2col">
        <ChartCard title="VO2 Max Trend">
          {vo2 ? <PlotlyChart data={vo2} /> : <div className="chart-loading">Loading...</div>}
        </ChartCard>
        <ChartCard title="Resting Heart Rate & HRV (Weekly)">
          {rhrHrv ? <PlotlyChart data={rhrHrv} /> : <div className="chart-loading">Loading...</div>}
        </ChartCard>
      </div>

      {/* Sleep */}
      <div id="sleep" className="section-header">Sleep</div>
      <div className="grid-2col">
        <ChartCard title="Sleep Stages (Weekly)">
          {sleepStages ? <PlotlyChart data={sleepStages} /> : <div className="chart-loading">Loading...</div>}
        </ChartCard>
        <ChartCard title="Total Sleep Duration Trend">
          {sleepDuration ? <PlotlyChart data={sleepDuration} /> : <div className="chart-loading">Loading...</div>}
        </ChartCard>
        <ChartCard title="Sleep Consistency (Bedtime & Wake Time)">
          {sleepConsistency ? <PlotlyChart data={sleepConsistency} /> : <div className="chart-loading">Loading...</div>}
        </ChartCard>
        <ChartCard title="Sleeping Wrist Temperature">
          {wristTemp ? <PlotlyChart data={wristTemp} /> : <div className="chart-loading">Loading...</div>}
        </ChartCard>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  );
}
