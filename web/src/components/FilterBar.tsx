import { useSearchParams } from 'react-router-dom';

export interface FilterDef {
  param: string;
  label: string;
  options: { value: string; label: string }[];
}

/** Bộ lọc một hàng phía trên biểu đồ. Trạng thái nằm trên URL để chia sẻ link là thấy đúng view. */
export function FilterBar({ filters }: { filters: FilterDef[] }) {
  const [params, setParams] = useSearchParams();
  return (
    <div className="filter-bar">
      {filters.map((f) => (
        <label key={f.param}>
          <span>{f.label}</span>
          <select
            value={params.get(f.param) ?? ''}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              if (e.target.value) next.set(f.param, e.target.value);
              else next.delete(f.param);
              setParams(next, { replace: true });
            }}
          >
            {f.options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      ))}
    </div>
  );
}
