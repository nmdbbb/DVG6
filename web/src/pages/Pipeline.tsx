import { useSearchParams } from 'react-router-dom';
import { apiGet } from '../api/client';
import { axisStyle, Chart } from '../components/Chart';
import { ChartCard } from '../components/ChartCard';
import { DataTable } from '../components/DataTable';
import { FilterBar } from '../components/FilterBar';
import { checkKind, QualityBadge } from '../components/QualityBadge';
import { fmtDateTime, fmtInt, fmtNumber } from '../lib/format';
import { useApi } from '../lib/useApi';

type QualityStatus = 'all' | 'failed' | 'passed';

export function Pipeline() {
  const [params] = useSearchParams();
  const source = params.get('source') ?? undefined;
  const mode = (params.get('mode') ?? undefined) as 'live' | 'mock' | undefined;
  const status = (params.get('status') ?? 'all') as QualityStatus;

  const sources = useApi(() => apiGet('/meta/sources'), 'sources');
  const batches = useApi(() => apiGet('/meta/batches', { query: { source, mode, limit: 50 } }), `batches:${source}:${mode}`);
  const runs = useApi(() => apiGet('/meta/quality/runs', { query: { limit: 20 } }), 'runs');
  const checks = useApi(() => apiGet('/meta/quality', { query: { status } }), `checks:${status}`);

  const err = sources.error ?? batches.error ?? runs.error ?? checks.error;
  if (err) return <p className="error">Không gọi được API: {err}</p>;

  // Lô cũ nhất bên trái; nhãn trục là thời điểm bắt đầu lô.
  const batchRows = [...(batches.data?.data ?? [])].reverse();
  const runRows = [...(runs.data?.data ?? [])].reverse();

  return (
    <>
      <h1>Sức khỏe pipeline</h1>
      <FilterBar
        filters={[
          {
            param: 'source',
            label: 'Nguồn',
            options: [
              { value: '', label: 'Tất cả nguồn' },
              ...(sources.data?.data ?? []).map((s) => ({ value: s.source_name, label: s.source_name })),
            ],
          },
          {
            param: 'mode',
            label: 'Đường lấy dữ liệu',
            options: [
              { value: '', label: 'live + mock' },
              { value: 'live', label: 'live (nguồn thật)' },
              { value: 'mock', label: 'mock (dự phòng)' },
            ],
          },
          {
            param: 'status',
            label: 'Kết quả check',
            options: [
              { value: '', label: 'Tất cả' },
              { value: 'failed', label: 'Chỉ check fail' },
              { value: 'passed', label: 'Chỉ check đạt' },
            ],
          },
        ]}
      />

      <div className="grid-2">
        <ChartCard title="Dòng lấy về và dòng mới ghi vào raw, theo lô" meta={batches.data?.meta} rows={batchRows} csvName="batches.csv">
          <Chart
            ariaLabel="Biểu đồ cột nhóm: số bản ghi connector lấy về và số dòng mới thực sự ghi vào raw ở mỗi lô nạp"
            option={(t) => ({
              color: [t.series1, t.series2],
              legend: { top: 0, left: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: t.textSecondary } },
              grid: { left: 8, right: 8, top: 32, bottom: 8, containLabel: true },
              tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
              xAxis: {
                type: 'category',
                data: batchRows.map((b) => [fmtDateTime(b.started_at), b.source_mode].join('\n')),
                ...axisStyle(t),
              },
              yAxis: { type: 'value', ...axisStyle(t) },
              series: [
                { name: 'Lấy về', type: 'bar', data: batchRows.map((b) => b.rows_fetched ?? 0), barMaxWidth: 16, barGap: '12%', itemStyle: { borderRadius: [4, 4, 0, 0] } },
                { name: 'Mới ghi (sau khử trùng lặp)', type: 'bar', data: batchRows.map((b) => b.row_count ?? 0), barMaxWidth: 16, itemStyle: { borderRadius: [4, 4, 0, 0] } },
              ],
            })}
          />
        </ChartCard>

        <ChartCard title="Kết quả quality qua các lần chạy" meta={runs.data?.meta} rows={runRows} csvName="quality_runs.csv">
          <Chart
            ariaLabel="Biểu đồ cột chồng: số check đạt, cảnh báo và lỗi ở mỗi lần chạy quality"
            option={(t) => ({
              color: [t.good, t.warning, t.critical],
              legend: { top: 0, left: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: t.textSecondary } },
              grid: { left: 8, right: 8, top: 32, bottom: 8, containLabel: true },
              tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
              xAxis: { type: 'category', data: runRows.map((r) => fmtDateTime(r.ran_at)), ...axisStyle(t) },
              yAxis: { type: 'value', minInterval: 1, ...axisStyle(t) },
              series: [
                { name: '✓ Đạt', data: runRows.map((r) => r.n_passed) },
                { name: '! Cảnh báo', data: runRows.map((r) => r.n_warning_failed) },
                { name: '✕ Lỗi (chặn pipeline)', data: runRows.map((r) => r.n_error_failed) },
              ].map((s) => ({
                ...s,
                type: 'bar',
                stack: 'checks',
                barMaxWidth: 22,
                itemStyle: { borderColor: t.surface, borderWidth: 1 },
              })),
            })}
          />
        </ChartCard>
      </div>

      <ChartCard title="Lịch sử lô nạp" meta={batches.data?.meta} rows={batches.data?.data} csvName="batches.csv">
        <DataTable
          rows={batches.data?.data ?? []}
          rowKey={(b) => b.batch_id}
          columns={[
            { key: 'status', header: 'Trạng thái', render: (b) => <QualityBadge kind={b.status as 'success' | 'failed' | 'running'} /> },
            { key: 'source', header: 'Nguồn', render: (b) => <code>{b.source_name}</code> },
            {
              key: 'mode',
              header: 'Đường',
              render: (b) => <span className={`mode mode-${b.source_mode}`}>{b.source_mode === 'mock' ? 'mock (dự phòng)' : 'live'}</span>,
            },
            { key: 'start', header: 'Bắt đầu', render: (b) => fmtDateTime(b.started_at) },
            { key: 'dur', header: 'Thời gian (s)', numeric: true, render: (b) => fmtNumber(b.duration_seconds) },
            { key: 'fetched', header: 'Lấy về', numeric: true, render: (b) => fmtInt(b.rows_fetched) },
            { key: 'new', header: 'Mới ghi', numeric: true, render: (b) => fmtInt(b.row_count) },
            { key: 'id', header: 'batch_id', render: (b) => <code className="muted">{b.batch_id.slice(0, 8)}</code> },
            { key: 'err', header: 'Lỗi', render: (b) => b.error_message ?? '' },
          ]}
        />
      </ChartCard>

      <ChartCard title="Check chất lượng — lần chạy mới nhất" meta={checks.data?.meta} rows={checks.data?.data} csvName="quality_checks.csv">
        <DataTable
          rows={checks.data?.data ?? []}
          rowKey={(c) => c.check_name}
          empty={status === 'failed' ? 'Không có check nào fail.' : 'Chưa chạy make quality.'}
          columns={[
            { key: 'res', header: 'Kết quả', render: (c) => <QualityBadge kind={checkKind(c.passed, c.severity)} /> },
            { key: 'sev', header: 'Mức', render: (c) => c.severity },
            { key: 'src', header: 'Nguồn check', render: (c) => c.check_source },
            { key: 'name', header: 'Check', render: (c) => <code>{c.check_name}</code> },
            { key: 'obs', header: 'Đo được', numeric: true, render: (c) => fmtNumber(c.observed_value) },
            { key: 'thr', header: 'Ngưỡng', render: (c) => c.threshold },
            { key: 'msg', header: 'Ghi chú', render: (c) => c.message ?? '' },
          ]}
        />
      </ChartCard>
    </>
  );
}
