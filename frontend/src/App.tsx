import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import KpiCards from "./components/KpiCards";
import ChartCard from "./components/ChartCard";
import PeriodDropdown from "./components/PeriodDropdown";
import PlotlyChart from "./components/PlotlyChart";
import ProfileModal from "./components/ProfileModal";
import WorkoutPanel from "./components/WorkoutPanel";
import {
  useKpis,
  useMeta,
  usePlotEndpoint,
  useSaveProfile,
  useWorkouts,
} from "./hooks/useHealthData";
import type { ThemeName } from "./theme/colors";

const queryClient = new QueryClient();

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "fitness", label: "Fitness" },
  { id: "heart", label: "Heart" },
  { id: "sleep", label: "Sleep" },
] as const;

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function loadTheme(): ThemeName {
  return localStorage.getItem("theme") === "dark" ? "dark" : "light";
}

function GearIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function Dashboard() {
  const { data: meta, isLoading: metaLoading } = useMeta();
  const saveProfile = useSaveProfile();

  const [theme, setTheme] = useState<ThemeName>(loadTheme);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [showProfile, setShowProfile] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("overview");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  const effectiveStart = start || (meta ? addDays(meta.max_date, -180) : "");
  const effectiveEnd = end || meta?.max_date || "";

  const handleDateChange = useCallback((s: string, e: string) => {
    setStart(s);
    setEnd(e);
  }, []);

  const gender = meta?.profile.gender || "male";

  const { data: kpis } = useKpis(effectiveStart, effectiveEnd);
  const { data: workoutsData } = useWorkouts(effectiveStart, effectiveEnd, theme);
  const { data: vo2 } = usePlotEndpoint("vo2", effectiveStart, effectiveEnd, { gender, theme });
  const { data: rhrHrv } = usePlotEndpoint("rhr-hrv", effectiveStart, effectiveEnd, { theme });
  const { data: sleepStages } = usePlotEndpoint("sleep-stages", effectiveStart, effectiveEnd, { theme });
  const { data: sleepDuration } = usePlotEndpoint("sleep-duration", effectiveStart, effectiveEnd, { theme });
  const { data: sleepConsistency } = usePlotEndpoint("sleep-consistency", effectiveStart, effectiveEnd, { theme });
  const { data: wristTemp } = usePlotEndpoint("wrist-temp", effectiveStart, effectiveEnd, { theme });

  const scrollToSection = (id: string) => {
    setActiveTab(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  if (metaLoading || !meta) {
    return <div className="dashboard"><div className="chart-loading">Loading...</div></div>;
  }

  return (
    <div className="dashboard">
      {/* Top nav */}
      <div className="top-nav">
        <div className="brand">
          <div className="brand-mark" />
          <span className="brand-name">Pulse</span>
        </div>
        <nav className="nav-pills">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`nav-pill ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => scrollToSection(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
        <div className="nav-right">
          <PeriodDropdown
            minDate={meta.min_date}
            maxDate={meta.max_date}
            onChange={handleDateChange}
          />
          <button
            className="theme-toggle"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
          >
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
          <button
            className="icon-btn"
            onClick={() => setShowProfile(true)}
            title="Profile settings"
            aria-label="Profile settings"
          >
            <GearIcon />
          </button>
        </div>
      </div>

      {showProfile && (
        <ProfileModal
          profile={meta.profile}
          onSave={(p) => saveProfile.mutate(p)}
          onClose={() => setShowProfile(false)}
        />
      )}

      {/* KPI strip */}
      <div id="overview">
        {kpis ? <KpiCards data={kpis} /> : <div className="chart-loading">Loading...</div>}
      </div>

      {/* Heart */}
      <div id="heart" className="grid-2col">
        <ChartCard title="VO2 Max Trend">
          {vo2 ? <PlotlyChart data={vo2} /> : <div className="chart-loading">Loading...</div>}
        </ChartCard>
        <ChartCard title="Resting HR & HRV — weekly">
          {rhrHrv ? <PlotlyChart data={rhrHrv} /> : <div className="chart-loading">Loading...</div>}
        </ChartCard>
      </div>

      {/* Workouts */}
      <div id="fitness">
        {workoutsData ? (
          <WorkoutPanel data={workoutsData} />
        ) : (
          <ChartCard title="Workouts">
            <div className="chart-loading">Loading...</div>
          </ChartCard>
        )}
      </div>

      {/* Sleep */}
      <div id="sleep" className="grid-2col">
        <ChartCard title="Sleep Stages — weekly">
          {sleepStages ? <PlotlyChart data={sleepStages} /> : <div className="chart-loading">Loading...</div>}
        </ChartCard>
        <ChartCard title="Sleep Duration Trend">
          {sleepDuration ? <PlotlyChart data={sleepDuration} /> : <div className="chart-loading">Loading...</div>}
        </ChartCard>
        <ChartCard title="Sleep Consistency">
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
