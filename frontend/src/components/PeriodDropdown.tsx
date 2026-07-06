import { useEffect, useRef, useState } from "react";

const PRESETS = [
  { key: "30d", label: "Last 30 days", days: 30 },
  { key: "90d", label: "Last 90 days", days: 90 },
  { key: "180d", label: "Last 6 months", days: 180 },
  { key: "1y", label: "Last year", days: 365 },
  { key: "2y", label: "Last 2 years", days: 730 },
  { key: "all", label: "All time", days: null },
] as const;

type PresetKey = (typeof PRESETS)[number]["key"];

interface Props {
  minDate: string;
  maxDate: string;
  onChange: (start: string, end: string) => void;
}

const MONTHS = [
  "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
  "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
];

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function daysBetween(a: string, b: string): number {
  const da = new Date(a + "T00:00:00").getTime();
  const db = new Date(b + "T00:00:00").getTime();
  return Math.round((db - da) / 86400000);
}

function formatReadout(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return `${MONTHS[d.getMonth()]} ${d.getDate()} ${d.getFullYear()}`;
}

export default function PeriodDropdown({ minDate, maxDate, onChange }: Props) {
  const effectiveMin = minDate < "2020-01-01" ? "2020-01-01" : minDate;

  const defaultStart = addDays(maxDate, -180);
  const [start, setStart] = useState(
    defaultStart < effectiveMin ? effectiveMin : defaultStart,
  );
  const [end, setEnd] = useState(maxDate);
  const [activeKey, setActiveKey] = useState<PresetKey | null>("180d");
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    onChange(start, end);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!open) return;
    const handleOutside = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, [open]);

  const presetDays = (days: number | null): number =>
    days === null ? daysBetween(effectiveMin, maxDate) : days;

  const handlePreset = (key: PresetKey, days: number | null) => {
    let newStart: string;
    if (days === null) {
      newStart = effectiveMin;
    } else {
      newStart = addDays(maxDate, -days);
      if (newStart < effectiveMin) newStart = effectiveMin;
    }
    setStart(newStart);
    setEnd(maxDate);
    setActiveKey(key);
    setOpen(false);
    onChange(newStart, maxDate);
  };

  const handleStartChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val) {
      setStart(val);
      setActiveKey(null);
      onChange(val, end);
    }
  };

  const handleEndChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val) {
      setEnd(val);
      setActiveKey(null);
      onChange(start, val);
    }
  };

  return (
    <div className="period-wrap" ref={wrapRef}>
      <span className="range-readout">
        {formatReadout(start)} → {formatReadout(end)}
      </span>
      <button className="period-btn" onClick={() => setOpen((o) => !o)}>
        {daysBetween(start, end)} DAYS <span className="caret">▼</span>
      </button>
      {open && (
        <div className="period-dropdown">
          {PRESETS.map((p) => (
            <button
              key={p.key}
              className={`period-option ${activeKey === p.key ? "active" : ""}`}
              onClick={() => handlePreset(p.key, p.days)}
            >
              {p.label}
              <span className="option-days">{presetDays(p.days)}d</span>
            </button>
          ))}
          <div className="period-custom">
            <span className="period-custom-label">Custom</span>
            <input
              type="date"
              value={start}
              min={effectiveMin}
              max={end}
              onChange={handleStartChange}
            />
            <input
              type="date"
              value={end}
              min={start}
              max={maxDate}
              onChange={handleEndChange}
            />
          </div>
        </div>
      )}
    </div>
  );
}
