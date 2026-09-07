import { useCallback, useEffect, useState } from "react";

import { api } from "./api";
import type { Gate, Meta } from "./types";

export function useFetch<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!!path);

  const reload = useCallback(() => {
    if (!path) return;
    setLoading(true);
    api
      .get<T>(path)
      .then((result) => {
        setData(result);
        setError(null);
      })
      .catch((cause: Error) => setError(cause.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);

  useEffect(reload, [reload]);

  return { data, error, loading, reload, setData };
}

export function useGates() {
  const { data } = useFetch<Gate[]>("/api/gates");
  return data ?? [];
}

export function useMeta() {
  const { data } = useFetch<Meta>("/api/meta");
  return data;
}
