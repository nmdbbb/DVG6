import { useEffect, useState } from 'react';

export interface ApiState<T> {
  data: T | undefined;
  error: string | undefined;
  loading: boolean;
}

/** Gọi API khi `key` đổi. `key` nên chứa mọi tham số lọc để tránh gọi thừa. */
export function useApi<T>(fetcher: () => Promise<T>, key: string): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({ data: undefined, error: undefined, loading: true });

  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true }));
    fetcher()
      .then((data) => alive && setState({ data, error: undefined, loading: false }))
      .catch((e: Error) => alive && setState({ data: undefined, error: e.message, loading: false }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return state;
}
