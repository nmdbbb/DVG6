/** Tải CSV từ chính các dòng mà endpoint trả về (cùng dữ liệu đang vẽ). */
export function downloadCsv(filename: string, rows: object[]): void {
  if (!rows.length) return;
  const cols = Object.keys(rows[0]);
  const esc = (v: unknown) => {
    const s = v == null ? '' : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const body = [cols.join(','), ...rows.map((r) => cols.map((c) => esc((r as Record<string, unknown>)[c])).join(','))];
  const blob = new Blob(['﻿' + body.join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
