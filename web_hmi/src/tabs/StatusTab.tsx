import { Activity, Cpu, Boxes, Network, ScrollText } from "lucide-react";
import { useTopic, useTopicLog, useTopicSeries } from "../ros/RosProvider";
import type { Header as HeaderMsg, RosLog, Utilization } from "../ros/types";
import { AI_MODELS } from "../ros/config";
import { useAlive } from "../lib/hooks";
import { GlassCard, KeyRow, RadialGauge, Sparkline, StatusOrb } from "../components/ui";
import type { OrbState } from "../components/ui";
import { cn } from "../lib/cn";

const getVal = (m: Utilization | undefined, name: string): number | undefined => {
  if (!m) return undefined;
  const i = m.component_names.indexOf(name);
  return i >= 0 ? m.component_values[i] : undefined;
};

const LEVELS: Record<number, { label: string; cls: string; bar: string }> = {
  10: { label: "DEBUG", cls: "text-faint", bar: "bg-white/15" },
  20: { label: "INFO", cls: "text-dim", bar: "bg-cyan/50" },
  30: { label: "WARN", cls: "text-amber", bar: "bg-amber" },
  40: { label: "ERROR", cls: "text-red", bar: "bg-red" },
  50: { label: "FATAL", cls: "text-red", bar: "bg-red" },
};

function GaugeCard({ label, value, series, accent }: { label: string; value?: number; series: number[]; accent: "cyan" | "violet" | "amber" | "emerald" }) {
  return (
    <GlassCard className="flex flex-col items-center">
      <RadialGauge label={label} value={value} accent={accent} />
      <div className="mt-2 h-[34px]">
        <Sparkline data={series} accent={accent} />
      </div>
    </GlassCard>
  );
}

export function StatusTab() {
  const util = useTopic<Utilization>("utilization");
  const heartbeat = useTopic<HeaderMsg>("heartbeat");
  const orchAlive = useAlive(heartbeat);
  const logs = useTopicLog<RosLog>("rosout", 24);

  const cpuS = useTopicSeries<Utilization>("utilization", (m) => getVal(m, "cpu"));
  const ramS = useTopicSeries<Utilization>("utilization", (m) => getVal(m, "ram"));
  const gpuS = useTopicSeries<Utilization>("utilization", (m) => getVal(m, "gpu"));
  const vramS = useTopicSeries<Utilization>("utilization", (m) => getVal(m, "vram"));

  const sub = (ok: boolean | undefined): { s: OrbState; t: string } =>
    ok === undefined ? { s: "idle", t: "—" } : ok ? { s: "ok", t: "online" } : { s: "bad", t: "down" };
  const nav2 = sub(util?.nav2_state);
  const moveit = sub(util?.moveit2_state);

  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-5">
      {/* gauges */}
      <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
        <GaugeCard label="CPU" value={getVal(util, "cpu")} series={cpuS} accent="cyan" />
        <GaugeCard label="RAM" value={getVal(util, "ram")} series={ramS} accent="violet" />
        <GaugeCard label="GPU" value={getVal(util, "gpu")} series={gpuS} accent="amber" />
        <GaugeCard label="VRAM" value={getVal(util, "vram")} series={vramS} accent="emerald" />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.7fr_1fr]">
        {/* models */}
        <GlassCard title="Inference stack" icon={<Cpu size={14} />} right={<span className="font-mono text-xs text-faint">gfx1151 · UMA</span>}>
          <div className="flex flex-col">
            <div className="kicker grid grid-cols-[1.6fr_0.8fr_0.8fr_0.6fr] gap-3 px-2 pb-2">
              <span>model</span>
              <span className="text-right">port</span>
              <span className="text-right">vram</span>
              <span className="text-right">slots</span>
            </div>
            {AI_MODELS.map((m) => (
              <div key={m.name} className="grid grid-cols-[1.6fr_0.8fr_0.8fr_0.6fr] items-center gap-3 rounded-lg border-t border-white/6 px-2 py-3">
                <div className="flex items-center gap-2.5">
                  <StatusOrb state="idle" />
                  <div className="min-w-0">
                    <div className="truncate font-medium text-fg">{m.name}</div>
                    <div className="truncate text-xs text-faint">{m.role}</div>
                  </div>
                </div>
                <div className="text-right font-mono text-sm text-dim">{m.port}</div>
                <div className="text-right font-mono text-sm text-dim">{m.vram}</div>
                <div className="text-right font-mono text-sm text-faint">0</div>
              </div>
            ))}
          </div>
        </GlassCard>

        {/* subsystems */}
        <GlassCard title="Subsystems" icon={<Network size={14} />}>
          <div className="grid grid-cols-2 gap-2.5">
            {[
              { name: "Nav2", ...nav2 },
              { name: "MoveIt2", ...moveit },
              { name: "Orchestrator", s: orchAlive ? "ok" : "bad", t: orchAlive ? "online" : "no beat" } as const,
              { name: "DDS shm", s: "idle", t: "—" } as const,
              { name: "Watchdog", s: "idle", t: "—" } as const,
              { name: "Entities", s: "idle", t: "—" } as const,
            ].map((x) => (
              <div key={x.name} className="glass-tint flex items-center justify-between rounded-xl px-3 py-2.5">
                <span className="text-sm text-fg">{x.name}</span>
                <span className="flex items-center gap-1.5 text-xs text-dim">
                  <StatusOrb state={x.s as OrbState} pulse={x.s === "ok"} />
                  {x.t}
                </span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.7fr_1fr]">
        {/* timeline */}
        <GlassCard title="Event timeline" icon={<ScrollText size={14} />} right={<span className="font-mono text-xs text-faint">{logs.length} events</span>}>
          <div className="max-h-72 space-y-1 overflow-y-auto pr-1">
            {logs.length === 0 && <p className="py-2 text-sm text-faint">waiting for /rosout…</p>}
            {logs.map((l, i) => {
              const lv = LEVELS[l.level] ?? LEVELS[20];
              return (
                <div key={i} className="flex items-start gap-3 rounded-lg px-2 py-1.5 hover:bg-white/[0.03]">
                  <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", lv.bar)} />
                  <div className="min-w-0 font-mono text-[12.5px]">
                    <span className={cn("font-semibold", lv.cls)}>{lv.label}</span>{" "}
                    <span className="text-faint">{l.name}</span>{" "}
                    <span className="text-fg/85">{l.msg}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </GlassCard>

        {/* llm + run stats */}
        <div className="flex flex-col gap-5">
          <GlassCard title="Last LLM call" icon={<Activity size={14} />}>
            <KeyRow label="Model" value="gpt-oss-20b" />
            <KeyRow label="Latency" value="—" />
            <KeyRow label="Tokens in / out" value="—" />
            <KeyRow label="Tool" value="—" />
          </GlassCard>
          <GlassCard title="Run stats" icon={<Boxes size={14} />}>
            <KeyRow label="Iters total" value="—" />
            <KeyRow label="Completed" value="—" />
            <KeyRow label="Tool errors" value="—" />
            <KeyRow label="lfm2-vl restarts" value="—" />
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
