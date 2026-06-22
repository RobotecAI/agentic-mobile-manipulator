import { useEffect, useRef, useState } from "react";

/** True while `value` keeps changing within `timeout` ms (freshness/heartbeat). */
export function useAlive(value: unknown, timeout = 4000): boolean {
  const last = useRef(0);
  const [, force] = useState(0);
  useEffect(() => {
    if (value !== undefined) last.current = performance.now();
  }, [value]);
  useEffect(() => {
    const id = window.setInterval(() => force((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, []);
  return performance.now() - last.current < timeout;
}
