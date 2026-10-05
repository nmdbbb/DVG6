import { apiGet } from '../api/client';
import { axisStyle, Chart } from '../components/Chart';
import { ChartCard } from '../components/ChartCard';
import { DataTable } from '../components/DataTable';
import { QualityBadge } from '../components/QualityBadge';
import { StatCard } from '../components/StatCard';
import { fmtDateTime, fmtInt, timeAgo } from '../lib/format';
import { useApi } from '../lib/useApi';

const LAYERS = ['raw', 'staging', 'core', 'analytics'];

function load() {
  return Promise.all([
    apiGet('/meta/sources'),
    apiGet('/meta/layers'),
    apiGet('/meta/batches', { query: { limit: 1 } }),
    apiGet('/meta/quality'),
  ]);
}

export function Overview() {
  const { data, error, loading } = useApi(load, 'overview');
  if (error) return <p className="error">Không gọi được API: {error}</p>;
  if (loading || !data) return <p className="loading">Đang tải…</p>;

  const [sources, layers, batches, quality] = data;
  const tables = layers.data.filter((t) => LAYERS.includes(t.schema_name));
  const sumRows = (pred: (s: string, t: string) => boolean) =>
    tables.filter((t) => pred(t.schema_name, t.table_name)).reduce((a, t) => a + t.row_count, 0);
  const lastBatch = batches.data[0];
  const checks = quality.data;
  const passed = checks.filter((c) => c.passed).length;
  const errorsFailed = checks.filter((c) => !c.passed && c.severity === 'error').length;
  const warningsFailed = checks.filter((c) => !c.passed && c.severity === 'warning').length;

  // Biểu đồ ngang: sắp theo tầng từ trên xuống (raw ở trên), nên đảo thứ tự cho trục category của ECharts.
  const bars = [...tables].reverse();

  return (
    <>
      <h1>Tổng quan warehouse</h1>
      <div className="stats">
        <StatCard label="Nguồn dữ liệu" value={sources.data.length} hint={sources.data.map((s) => s.source_name).join(', ')} />
        <StatCard label="Dòng trong raw" value={fmtInt(sumRows((s) => s === 'raw'))} hint="tất cả lô, kể cả lô fail" />
        <StatCard
          label="Dòng trong fact (core)"
          value={fmtInt(sumRows((s, t) => s === 'core' && t.startsWith('fct_')))}
          hint="sau làm sạch và khử trùng lặp"
        />
        <StatCard
          label="Lô nạp gần nhất"
          value={timeAgo(lastBatch?.started_at)}
          hint={lastBatch ? <QualityBadge kind={lastBatch.status as 'success' | 'failed' | 'running'} /> : 'chưa có lô'}
        />
        <StatCard
          label="Quality lần gần nhất"
          value={checks.length ? `${passed}/${checks.length} đạt` : '—'}
          hint={
            checks.length ? (
              errorsFailed ? (
                <QualityBadge kind="error" />
              ) : warningsFailed ? (
                <QualityBadge kind="warning" />
              ) : (
                <QualityBadge kind="pass" />
              )
            ) : (
              'chưa chạy'
            )
          }
        />
      </div>

      <ChartCard title="Số dòng ở từng tầng" meta={layers.meta} rows={tables} csvName="layer_row_counts.csv">
        <Chart
          ariaLabel="Biểu đồ cột ngang số dòng của từng bảng theo tầng raw, staging, core, analytics"
          height={Math.max(180, bars.length * 36 + 40)}
          option={(t) => ({
            grid: { left: 8, right: 64, top: 8, bottom: 24, containLabel: true },
            tooltip: { trigger: 'item', formatter: (p: { name: string; value: number }) => `${p.name}<br/><b>${fmtInt(p.value)}</b> dòng` },
            xAxis: { type: 'value', ...axisStyle(t) },
            yAxis: {
              type: 'category',
              data: bars.map((b) => `${b.schema_name}.${b.table_name}`),
              ...axisStyle(t),
              axisLabel: { color: t.textSecondary, fontSize: 12 },
              splitLine: { show: false },
            },
            series: [
              {
                type: 'bar',
                data: bars.map((b) => b.row_count),
                barMaxWidth: 18,
                itemStyle: { color: t.series1, borderRadius: [0, 4, 4, 0] },
                emphasis: { itemStyle: { opacity: 0.8 } },
                label: { show: true, position: 'right', color: t.textSecondary, formatter: (p: { value: number }) => fmtInt(p.value) },
              },
            ],
          })}
        />
      </ChartCard>

      <ChartCard title="Nguồn dữ liệu" meta={sources.meta} rows={sources.data} csvName="sources.csv">
        <DataTable
          rows={sources.data}
          rowKey={(s) => s.source_name}
          columns={[
            { key: 'name', header: 'Nguồn', render: (s) => <code>{s.source_name}</code> },
            { key: 'desc', header: 'Mô tả', render: (s) => s.description },
            { key: 'license', header: 'Giấy phép', render: (s) => s.license },
            { key: 'freq', header: 'Cập nhật', render: (s) => s.update_frequency },
            { key: 'batches', header: 'Số lô', numeric: true, render: (s) => fmtInt(s.batch_count) },
            { key: 'rows', header: 'Dòng đã nạp', numeric: true, render: (s) => fmtInt(s.total_rows) },
            { key: 'last', header: 'Lô gần nhất', render: (s) => fmtDateTime(s.last_batch_at) },
          ]}
        />
      </ChartCard>
    </>
  );
}
