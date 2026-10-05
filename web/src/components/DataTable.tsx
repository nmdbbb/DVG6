import type { ReactNode } from 'react';

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  numeric?: boolean;
}

interface Props<T> {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  selectedKey?: string;
  empty?: string;
}

export function DataTable<T>({ rows, columns, rowKey, onRowClick, selectedKey, empty }: Props<T>) {
  if (!rows.length) return <p className="empty">{empty ?? 'Chưa có dữ liệu.'}</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.numeric ? 'num' : undefined}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const k = rowKey(row);
            return (
              <tr
                key={k}
                className={[onRowClick ? 'clickable' : '', k === selectedKey ? 'selected' : ''].join(' ')}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                onKeyDown={onRowClick ? (e) => e.key === 'Enter' && onRowClick(row) : undefined}
              >
                {columns.map((c) => (
                  <td key={c.key} className={c.numeric ? 'num' : undefined}>
                    {c.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
