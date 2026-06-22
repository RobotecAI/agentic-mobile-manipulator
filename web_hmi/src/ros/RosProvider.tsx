import ROSLIB from "./roslib";
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import type { ReactNode } from "react";
import { CONFIG, PUBLISHERS, SERVICES, TOPICS } from "./config";
import type { PublisherKey, ServiceKey, TopicKey } from "./config";
import { RosStore } from "./store";
import { MockEngine } from "./mock";
import type { ConnectionState, ServiceResult } from "./types";

interface RosContextValue {
  state: ConnectionState;
  store: RosStore;
  mock: MockEngine;
  callService: (key: ServiceKey) => Promise<ServiceResult>;
  publish: (key: PublisherKey, message: Record<string, unknown>) => void;
}

const RosContext = createContext<RosContextValue | null>(null);

export function RosProvider({ children }: { children: ReactNode }) {
  const store = useMemo(() => new RosStore(), []);
  const mock = useMemo(() => new MockEngine(store), [store]);
  const [state, setState] = useState<ConnectionState>(CONFIG.forceDemo ? "demo" : "connecting");

  const rosRef = useRef<ROSLIB.Ros | null>(null);
  const pubRef = useRef<Map<PublisherKey, ROSLIB.Topic>>(new Map());

  useEffect(() => {
    if (CONFIG.forceDemo) {
      mock.start();
      return () => mock.stop();
    }

    const ros = new ROSLIB.Ros({ url: CONFIG.rosbridgeUrl });
    rosRef.current = ros;
    let demoFallback: number | undefined;
    let live = false;

    // If rosbridge does not answer quickly, fall back to the demo feed so the
    // operator always sees a populated UI.
    demoFallback = window.setTimeout(() => {
      if (!live) {
        setState("demo");
        mock.start();
      }
    }, 2500);

    ros.on("connection", () => {
      live = true;
      window.clearTimeout(demoFallback);
      mock.stop();
      setState("connected");

      for (const key of Object.keys(TOPICS) as TopicKey[]) {
        const def = TOPICS[key];
        const topic = new ROSLIB.Topic({ ros, name: def.name, messageType: def.type });
        topic.subscribe((msg) => store.set(key, msg));
      }
    });

    ros.on("close", () => {
      if (live) setState("closed");
    });
    ros.on("error", () => {
      // handled by the demo fallback timer
    });

    return () => {
      window.clearTimeout(demoFallback);
      mock.stop();
      ros.close();
    };
  }, [store, mock]);

  const value = useMemo<RosContextValue>(
    () => ({
      state,
      store,
      mock,
      publish(key, message) {
        const ros = rosRef.current;
        if (!ros || state !== "connected") {
          // demo / offline: no-op besides a console trace
          console.info("[demo] publish", PUBLISHERS[key].name, message);
          return;
        }
        let topic = pubRef.current.get(key);
        if (!topic) {
          topic = new ROSLIB.Topic({ ros, name: PUBLISHERS[key].name, messageType: PUBLISHERS[key].type });
          pubRef.current.set(key, topic);
        }
        topic.publish(new ROSLIB.Message(message));
      },
      callService(key) {
        return new Promise<ServiceResult>((resolve) => {
          const ros = rosRef.current;
          if (!ros || state !== "connected") {
            console.info("[demo] callService", SERVICES[key]);
            resolve({ success: true, message: "demo" });
            return;
          }
          const svc = new ROSLIB.Service({ ros, name: SERVICES[key], serviceType: "std_srvs/srv/Trigger" });
          svc.callService(
            new ROSLIB.ServiceRequest({}),
            (res: ServiceResult) => resolve(res),
            (err: string) => resolve({ success: false, message: err }),
          );
        });
      },
    }),
    [state, store, mock],
  );

  return <RosContext.Provider value={value}>{children}</RosContext.Provider>;
}

export function useRos(): RosContextValue {
  const ctx = useContext(RosContext);
  if (!ctx) throw new Error("useRos must be used within <RosProvider>");
  return ctx;
}

/** Latest message on a topic. */
export function useTopic<T>(key: TopicKey): T | undefined {
  const { store } = useRos();
  return useSyncExternalStore(
    (cb) => store.subscribe(key, cb),
    () => store.get<T>(key),
  );
}

/** Rolling numeric series sampled from a topic (oldest -> newest), for sparklines. */
export function useTopicSeries<T>(key: TopicKey, pick: (m: T) => number | undefined, max = 40): number[] {
  const { store } = useRos();
  const [series, setSeries] = useState<number[]>([]);
  useEffect(() => {
    return store.subscribe(key, () => {
      const v = store.get<T>(key);
      if (v === undefined) return;
      const n = pick(v);
      if (n === undefined || !Number.isFinite(n)) return;
      setSeries((prev) => [...prev, n].slice(-max));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store, key, max]);
  return series;
}

/** Rolling log of the most recent messages on a topic (newest first). */
export function useTopicLog<T>(key: TopicKey, max = 30): T[] {
  const { store } = useRos();
  const [items, setItems] = useState<T[]>([]);
  useEffect(() => {
    return store.subscribe(key, () => {
      const v = store.get<T>(key);
      if (v === undefined) return;
      setItems((prev) => [v, ...prev].slice(0, max));
    });
  }, [store, key, max]);
  return items;
}
