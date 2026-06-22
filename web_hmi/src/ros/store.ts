import type { TopicKey } from "./config";

type Listener = () => void;

/**
 * Minimal external store holding the latest message per topic. Components read
 * it through useSyncExternalStore so only the consumers of a given topic
 * re-render when that topic updates.
 */
export class RosStore {
  private values = new Map<string, unknown>();
  private listeners = new Map<string, Set<Listener>>();

  get<T>(key: TopicKey): T | undefined {
    return this.values.get(key) as T | undefined;
  }

  set<T>(key: TopicKey, value: T): void {
    this.values.set(key, value);
    this.listeners.get(key)?.forEach((l) => l());
  }

  subscribe(key: TopicKey, listener: Listener): () => void {
    let set = this.listeners.get(key);
    if (!set) {
      set = new Set();
      this.listeners.set(key, set);
    }
    set.add(listener);
    return () => set!.delete(listener);
  }
}
