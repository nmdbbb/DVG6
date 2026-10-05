import type { ReactNode } from 'react';

interface Props {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
}

export function StatCard({ label, value, hint }: Props) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  );
}
