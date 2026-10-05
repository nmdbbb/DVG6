import type { ReactNode } from 'react';
import type { ResponseMeta } from '../api/client';
import { downloadCsv } from '../lib/csv';
import { fmtDateTime } from '../lib/format';

interface Props {
  title: string;
  meta?: ResponseMeta;
  rows?: object[];
  csvName?: string;
  children: ReactNode;
}

/** Khung chung cho mọi biểu đồ/bảng: tiêu đề, as_of + nguồn ngay dưới, nút tải CSV. */
export function ChartCard({ title, meta, rows, csvName, children }: Props) {
  return (
    <section className="card">
      <header className="card-head">
        <div>
          <h2>{title}</h2>
          {meta && (
            <p className="provenance">
              Dữ liệu tới {fmtDateTime(meta.as_of)} · nguồn <code>{meta.source}</code> · {meta.row_count} dòng
            </p>
          )}
        </div>
        {rows && csvName && (
          <button className="btn-ghost" onClick={() => downloadCsv(csvName, rows)} disabled={!rows.length}>
            Tải CSV
          </button>
        )}
      </header>
      {children}
    </section>
  );
}
