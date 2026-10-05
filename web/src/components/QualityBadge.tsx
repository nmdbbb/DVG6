// Trạng thái luôn đi kèm biểu tượng + chữ, không bao giờ chỉ dựa vào màu.
type Kind = 'pass' | 'warning' | 'error' | 'running' | 'success' | 'failed';

const LOOK: Record<Kind, { icon: string; label: string; tone: string }> = {
  pass: { icon: '✓', label: 'Đạt', tone: 'good' },
  success: { icon: '✓', label: 'success', tone: 'good' },
  warning: { icon: '!', label: 'Cảnh báo', tone: 'warning' },
  error: { icon: '✕', label: 'Lỗi', tone: 'critical' },
  failed: { icon: '✕', label: 'failed', tone: 'critical' },
  running: { icon: '…', label: 'running', tone: 'neutral' },
};

export function QualityBadge({ kind }: { kind: Kind }) {
  const look = LOOK[kind];
  return (
    <span className={`badge badge-${look.tone}`}>
      <span aria-hidden="true">{look.icon}</span> {look.label}
    </span>
  );
}

export function checkKind(passed: boolean, severity: string): Kind {
  if (passed) return 'pass';
  return severity === 'error' ? 'error' : 'warning';
}
