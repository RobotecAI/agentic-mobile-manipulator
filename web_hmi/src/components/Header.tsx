import { useEffect, useState } from "react";
import { Hexagon, Power } from "lucide-react";
import { useRos, useTopic } from "../ros/RosProvider";
import type { Header as HeaderMsg } from "../ros/types";
import { useAlive } from "../lib/hooks";
import { Button, Chip } from "./ui";
import type { OrbState } from "./ui";

function useClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);
  return now;
}

export function Header() {
  const { state, publish } = useRos();
  const heartbeat = useTopic<HeaderMsg>("heartbeat");
  const agentAlive = useAlive(heartbeat);
  const now = useClock();

  const link: Record<string, { s: OrbState; label: string }> = {
    connected: { s: "ok", label: "rosbridge · live" },
    demo: { s: "warn", label: "demo feed" },
    connecting: { s: "idle", label: "connecting…" },
    closed: { s: "bad", label: "disconnected" },
  };
  const l = link[state] ?? link.connecting;

  return (
    <header className="relative z-20 flex h-16 shrink-0 items-center gap-4 border-b border-white/8 bg-white/[0.02] px-6 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <div className="relative grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-cyan/30 to-violet/30 ring-1 ring-white/15">
          <Hexagon size={18} className="text-cyan" />
        </div>
        <div className="leading-tight">
          <div className="font-display text-[15px] font-medium tracking-tight">
            Kairos<span className="text-gradient font-semibold">+</span> Command
          </div>
          <div className="text-[11px] text-faint">Agentic warehouse manipulator</div>
        </div>
      </div>

      <div className="flex-1" />

      <span className="hidden font-mono text-sm tnum text-dim lg:block">
        {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
      </span>

      <div className="hidden items-center gap-2 md:flex">
        <Chip state={l.s} pulse={state === "connected"}>
          {l.label}
        </Chip>
        <Chip state={agentAlive ? "ok" : "bad"} pulse={agentAlive}>
          {agentAlive ? "agent online" : "agent offline"}
        </Chip>
      </div>

      <Button variant="danger" className="gap-2 px-5" onClick={() => publish("stop", { data: "" })} title="Publish to /emergency_stop">
        <Power size={16} strokeWidth={2.5} />
        E-STOP
      </Button>
    </header>
  );
}
