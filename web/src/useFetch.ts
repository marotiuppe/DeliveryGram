import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";

type State<T> = { data: T | null; loading: boolean; error: string | null; stale: boolean };

/** GET with a saved copy: when the network fails, the last good response is shown (marked stale). */
export function useFetch<T>(path: string | null, pollMs = 0) {
  const [state, setState] = useState<State<T>>({ data: null, loading: !!path, error: null, stale: false });
  const alive = useRef(true);

  const run = useCallback(async () => {
    if (!path) return;
    const key = "dg_cache:" + path;
    try {
      const data = await api<T>(path);
      try { localStorage.setItem(key, JSON.stringify(data)); } catch { /* storage full */ }
      if (alive.current) setState({ data, loading: false, error: null, stale: false });
    } catch (e) {
      const offline = e instanceof ApiError && e.status === 0;
      let cached: T | null = null;
      if (offline) {
        try { const raw = localStorage.getItem(key); cached = raw ? (JSON.parse(raw) as T) : null; } catch { /* ignore */ }
      }
      if (!alive.current) return;
      if (cached) setState({ data: cached, loading: false, error: null, stale: true });
      else setState((s) => ({ ...s, loading: false, error: e instanceof ApiError ? e.message : "error" }));
    }
  }, [path]);

  useEffect(() => {
    alive.current = true;
    setState({ data: null, loading: !!path, error: null, stale: false });
    void run();
    const timer = pollMs ? window.setInterval(() => void run(), pollMs) : 0;
    return () => { alive.current = false; if (timer) window.clearInterval(timer); };
  }, [path, pollMs, run]);

  return { ...state, reload: run };
}
