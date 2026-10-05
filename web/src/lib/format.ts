const nf = new Intl.NumberFormat('vi-VN');
const df = new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short' });

export const fmtInt = (n: number | null | undefined) => (n == null ? '—' : nf.format(n));

export const fmtDateTime = (s: string | null | undefined) => (s ? df.format(new Date(s)) : '—');

export const fmtPct = (v: number | string | null | undefined, digits = 1) =>
  v == null ? '—' : `${(Number(v) * 100).toFixed(digits)}%`;

export function fmtNumber(v: number | string | null | undefined): string {
  if (v == null) return '—';
  const n = Number(v);
  return Number.isInteger(n) ? nf.format(n) : n.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
}

export function timeAgo(s: string | null | undefined): string {
  if (!s) return '—';
  const mins = Math.round((Date.now() - new Date(s).getTime()) / 60000);
  if (mins < 1) return 'vừa xong';
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours} giờ trước`;
  return `${Math.round(hours / 24)} ngày trước`;
}
