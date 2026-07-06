/** Horizon Mono design tokens — Solar Coral accent, light/dark themes. */

export const ACCENT = "#E85D3A";
export const ACCENT_DEEP = "#B8401F";

export type ThemeName = "light" | "dark";

export interface ThemeTokens {
  bg: string;
  card: string;
  border: string;
  text: string;
  sub: string;
  navBg: string;
  grid: string;
  tick: string;
  muted: string;
  dot: string;
  hrv: string;
}

export const THEMES: Record<ThemeName, ThemeTokens> = {
  light: {
    bg: "#F4F4F6",
    card: "#FFFFFF",
    border: "#E4E5EA",
    text: "#141519",
    sub: "#73767F",
    navBg: "#E9EAEF",
    grid: "rgba(20,21,25,0.07)",
    tick: "#8A8D96",
    muted: "#D9DBE2",
    dot: "#B8BBC6",
    hrv: "#C39B8D",
  },
  dark: {
    bg: "#0E0F13",
    card: "#16181E",
    border: "#262932",
    text: "#F0F1F5",
    sub: "#8D919E",
    navBg: "#1C1F27",
    grid: "rgba(255,255,255,0.08)",
    tick: "#767B88",
    muted: "#2A2E3A",
    dot: "#3E4454",
    hrv: "#D89A85",
  },
};
