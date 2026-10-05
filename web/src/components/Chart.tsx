import * as echarts from 'echarts';
import { useEffect, useRef, useState } from 'react';
import { fmtInt } from '../lib/format';
import { chartTokens } from '../lib/theme';

type Tokens = ReturnType<typeof chartTokens>;

interface Props {
  /** Dựng option từ token màu hiện tại, để sáng/tối luôn đúng bậc màu. */
  option: (t: Tokens) => echarts.EChartsCoreOption;
  height?: number;
  ariaLabel: string;
}

function useColorScheme(): string {
  const query = '(prefers-color-scheme: dark)';
  const [scheme, setScheme] = useState(() => (matchMedia(query).matches ? 'dark' : 'light'));
  useEffect(() => {
    const mq = matchMedia(query);
    const on = () => setScheme(mq.matches ? 'dark' : 'light');
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return scheme;
}

export function Chart({ option, height = 280, ariaLabel }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts>();
  const scheme = useColorScheme();

  useEffect(() => {
    if (!ref.current) return;
    chart.current = echarts.init(ref.current, undefined, { renderer: 'svg' });
    const ro = new ResizeObserver(() => chart.current?.resize());
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.current?.dispose();
    };
  }, []);

  useEffect(() => {
    const t = chartTokens();
    chart.current?.setOption(
      {
        aria: { enabled: true },
        textStyle: { fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif', color: t.textSecondary },
        tooltip: {
          backgroundColor: t.surface,
          borderColor: t.axis,
          textStyle: { color: t.text, fontSize: 12 },
        },
        ...option(t),
      },
      true,
    );
  }, [option, scheme]);

  return <div ref={ref} role="img" aria-label={ariaLabel} style={{ width: '100%', height }} />;
}

/** Trục và lưới chuẩn: lưới mảnh, nhãn màu muted. */
export function axisStyle(t: Tokens) {
  return {
    axisLine: { lineStyle: { color: t.axis } },
    axisTick: { show: false },
    axisLabel: { color: t.muted, fontSize: 11, formatter: (v: number | string) => (typeof v === 'number' ? fmtInt(v) : v) },
    splitLine: { lineStyle: { color: t.grid } },
  };
}
