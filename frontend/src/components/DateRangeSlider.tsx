import { useCallback, useEffect, useMemo, useState } from "react";

const PRESETS = [30, 60, 90, 180, 360, 540, 720, 1080] as const;

interface Props {
  minDate: string;
  maxDate: string;
  onChange: (start: string, end: string) => void;
}

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

export default function DateRangeSlider({ minDate, maxDate, onChange }: Props) {
  const effectiveMin = minDate < "2020-01-01" ? "2020-01-01" : minDate;

  const defaultStart = addDays(maxDate, -180);
  const [start, setStart] = useState(
    defaultStart < effectiveMin ? effectiveMin : defaultStart,
  );
  const [end, setEnd] = useState(maxDate);
  const [activePreset, setActivePreset] = useState<number | string | null>(180);

  const selectedDays = useMemo(() => daysBetween(start, end), [start, end]);

  useEffect(() => {
    onChange(start, end);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handlePreset = useCallback(
    (preset: number | "all") => {
      let newStart: string;
      if (preset === "all") {
        newStart = effectiveMin;
      } else {
        newStart = addDays(maxDate, -preset);
        if (newStart < effectiveMin) newStart = effectiveMin;
      }
      setStart(newStart);
      setEnd(maxDate);
      setActivePreset(preset);
      onChange(newStart, maxDate);
    },
    [effectiveMin, maxDate, onChange],
  );

  const handleStartChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val) {
      setStart(val);
      setActivePreset(null);
      onChange(val, end);
    }
  };

  const handleEndChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val) {
      setEnd(val);
      setActivePreset(null);
      onChange(start, val);
    }
  };

  return (
    <div className="date-control">
      <span className="days-combo">
        <span className="days-combo-label">Total Days</span>
        <span className="days-combo-value">{selectedDays}</span>
      </span>
      <div className="preset-row">
        {PRESETS.map((d) => (
          <button
            key={d}
            className={`preset-btn ${activePreset === d ? "active" : ""}`}
            onClick={() => handlePreset(d)}
          >
            {d}
          </button>
        ))}
        <button
          className={`preset-btn ${activePreset === "all" ? "active" : ""}`}
          onClick={() => handlePreset("all")}
        >
          All
        </button>
      </div>

      <div className="date-pickers">
        <label className="date-picker-field">
          <span className="date-picker-label">Start</span>
          <input
            type="date"
            value={start}
            min={effectiveMin}
            max={end}
            onChange={handleStartChange}
          />
        </label>
        <span className="date-picker-sep">&mdash;</span>
        <label className="date-picker-field">
          <span className="date-picker-label">End</span>
          <input
            type="date"
            value={end}
            min={start}
            max={maxDate}
            onChange={handleEndChange}
          />
        </label>
      </div>
    </div>
  );
}
