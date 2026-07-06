import type { ReactNode } from "react";

interface Props {
  title: string;
  children: ReactNode;
  className?: string;
}

export default function ChartCard({ title, children, className = "" }: Props) {
  return (
    <div className={`card ${className}`}>
      <h3 className="card-title">{title}</h3>
      {children}
    </div>
  );
}
