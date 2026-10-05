import { useSearchParams } from 'react-router-dom';
import { apiGet } from '../api/client';
import { ChartCard } from '../components/ChartCard';
import { DataTable } from '../components/DataTable';
import { FilterBar } from '../components/FilterBar';
import { fmtInt, fmtPct } from '../lib/format';
import { useApi } from '../lib/useApi';

const SCHEMAS = ['raw', 'staging', 'core', 'analytics', 'meta'];

export function Catalog() {
  const [params, setParams] = useSearchParams();
  const schema = params.get('schema') ?? undefined;
  const selected = params.get('table') ?? undefined;

  const tables = useApi(() => apiGet('/catalog/tables', { query: { schema } }), `tables:${schema}`);
  const columns = useApi(
    () =>
      selected
        ? apiGet('/catalog/tables/{name}/columns', { path: { name: selected } })
        : Promise.resolve(undefined),
    `columns:${selected}`,
  );

  if (tables.error) return <p className="error">Không gọi được API: {tables.error}</p>;

  return (
    <>
      <h1>Data catalog</h1>
      <p className="lede">
        Mô tả bảng và cột đọc thẳng từ <code>COMMENT ON</code> trong Postgres (migration và dbt <code>persist_docs</code>), nên
        không lệch với database. Số dòng và tỉ lệ NULL do <code>make quality</code> đo.
      </p>
      <FilterBar
        filters={[
          {
            param: 'schema',
            label: 'Tầng',
            options: [{ value: '', label: 'Tất cả tầng' }, ...SCHEMAS.map((s) => ({ value: s, label: s }))],
          },
        ]}
      />

      <div className="grid-2 catalog">
        <ChartCard title="Bảng" meta={tables.data?.meta} rows={tables.data?.data} csvName="catalog_tables.csv">
          <DataTable
            rows={tables.data?.data ?? []}
            rowKey={(t) => `${t.schema_name}.${t.table_name}`}
            selectedKey={selected}
            onRowClick={(t) => {
              const next = new URLSearchParams(params);
              next.set('table', `${t.schema_name}.${t.table_name}`);
              setParams(next, { replace: true });
            }}
            columns={[
              { key: 'name', header: 'Bảng', render: (t) => <code>{`${t.schema_name}.${t.table_name}`}</code> },
              { key: 'kind', header: 'Loại', render: (t) => t.kind },
              { key: 'rows', header: 'Số dòng', numeric: true, render: (t) => fmtInt(t.row_count) },
              { key: 'comment', header: 'Mô tả', render: (t) => <span className="clamp">{t.comment ?? '— thiếu comment —'}</span> },
            ]}
          />
        </ChartCard>

        <ChartCard
          title={selected ? `Cột của ${selected}` : 'Chọn một bảng để xem cột'}
          meta={columns.data?.meta}
          rows={columns.data?.data}
          csvName={`catalog_${selected}.csv`}
        >
          {columns.error && <p className="error">{columns.error}</p>}
          {selected && columns.data && (
            <DataTable
              rows={columns.data.data}
              rowKey={(c) => c.column_name}
              columns={[
                { key: 'name', header: 'Cột', render: (c) => <code>{c.column_name}</code> },
                { key: 'type', header: 'Kiểu', render: (c) => <code className="muted">{c.data_type}</code> },
                { key: 'null', header: 'NULL', numeric: true, render: (c) => fmtPct(c.null_rate) },
                { key: 'comment', header: 'Ý nghĩa', render: (c) => c.comment ?? '— thiếu comment —' },
              ]}
            />
          )}
        </ChartCard>
      </div>
    </>
  );
}
