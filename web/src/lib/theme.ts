// Màu biểu đồ đọc từ CSS custom property (styles.css), nên sáng/tối đổi ở một chỗ.
export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function chartTokens() {
  return {
    series1: cssVar('--series-1'),
    series2: cssVar('--series-2'),
    good: cssVar('--status-good'),
    warning: cssVar('--status-warning'),
    critical: cssVar('--status-critical'),
    text: cssVar('--text-primary'),
    textSecondary: cssVar('--text-secondary'),
    muted: cssVar('--text-muted'),
    grid: cssVar('--grid'),
    axis: cssVar('--axis'),
    surface: cssVar('--surface-1'),
  };
}
