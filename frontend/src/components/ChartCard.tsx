import type { ReactNode } from "react";

interface Props {
  title: string;
  children: ReactNode;
  className?: string;
}

export default function ChartCard({ title, children, className = "" }: Props) {
  return (
    <div className={`chart-card ${className}`}>
      <h3>{title}</h3>
      {children}
    </div>
  );
}
