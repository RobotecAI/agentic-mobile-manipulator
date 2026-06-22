import { useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Boxes,
  Brush,
  Check,
  Eraser,
  PackageCheck,
  PackageSearch,
  SendHorizontal,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react";
import { useRos } from "../ros/RosProvider";
import type { ServiceKey } from "../ros/config";
import { PROMPTS, RACKS, SHIPMENT_ITEMS } from "../ros/config";
import { Button, GlassCard, Kicker } from "../components/ui";
import { cn } from "../lib/cn";

function useFlash() {
  const [done, setDone] = useState(false);
  return {
    done,
    flash() {
      setDone(true);
      window.setTimeout(() => setDone(false), 1400);
    },
  };
}

function MissionCard({
  icon,
  title,
  desc,
  cta,
  accent,
  extra,
  onRun,
}: {
  icon: ReactNode;
  title: string;
  desc: string;
  cta: string;
  accent: string;
  extra?: ReactNode;
  onRun: () => void;
}) {
  const { done, flash } = useFlash();
  return (
    <GlassCard className="group flex flex-col transition-transform duration-200 hover:-translate-y-1">
      <div
        className="mb-3 grid h-11 w-11 place-items-center rounded-xl text-[#04121a]"
        style={{ background: accent }}
      >
        {icon}
      </div>
      <h3 className="font-display text-lg font-medium text-fg">{title}</h3>
      <p className="mb-4 mt-1 flex-1 text-sm leading-relaxed text-dim">{desc}</p>
      {extra}
      <Button
        variant="ghost"
        className="w-full group-hover:border-white/20"
        onClick={() => {
          onRun();
          flash();
        }}
      >
        {done ? <Check size={16} className="text-emerald" /> : null}
        {done ? "Dispatched" : cta}
      </Button>
    </GlassCard>
  );
}

function ScenarioTile({
  icon,
  title,
  desc,
  svc,
  accent,
}: {
  icon: ReactNode;
  title: string;
  desc: string;
  svc: ServiceKey;
  accent: string;
}) {
  const { callService } = useRos();
  const { done, flash } = useFlash();
  return (
    <button
      onClick={() => {
        void callService(svc);
        flash();
      }}
      className="glass-tint group relative overflow-hidden rounded-2xl p-4 text-left transition-all duration-200 hover:-translate-y-1 hover:border-white/20"
    >
      <div className="absolute -right-6 -top-6 h-20 w-20 rounded-full opacity-20 blur-2xl transition-opacity group-hover:opacity-40" style={{ background: accent }} />
      <div className="mb-3 grid h-9 w-9 place-items-center rounded-lg text-[#04121a]" style={{ background: accent }}>
        {icon}
      </div>
      <div className="font-display text-base font-medium text-fg">{title}</div>
      <p className="mt-0.5 text-xs leading-relaxed text-dim">{desc}</p>
      <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-cyan">
        {done ? <Check size={13} /> : null}
        {done ? "Spawned" : "Spawn scenario →"}
      </div>
    </button>
  );
}

export function ControlTab() {
  const { publish, callService } = useRos();
  const [rackIdx, setRackIdx] = useState(0);
  const [items, setItems] = useState<Record<string, boolean>>({});
  const [freeform, setFreeform] = useState("");
  const send = (text: string) => publish("userTasks", { data: text });
  const teleop = (lin: number, ang: number) =>
    publish("cmdVel", { linear: { x: lin, y: 0, z: 0 }, angular: { x: 0, y: 0, z: ang } });

  const runFree = () => {
    if (freeform.trim()) {
      send(freeform.trim());
      setFreeform("");
    }
  };

  const suggestions = ["Bring two hammers to the packing table", "Check aisle C for spills", "Restock rack B02"];

  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-6">
      {/* hero command */}
      <GlassCard glow className="overflow-visible">
        <div className="pointer-events-none absolute right-0 top-0 h-40 w-40 rounded-full bg-cyan/20 blur-3xl" />
        <Kicker>natural-language command</Kicker>
        <h2 className="mt-1 font-display text-2xl font-medium">
          Tell the robot <span className="text-gradient">anything</span>.
        </h2>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input
            value={freeform}
            onChange={(e) => setFreeform(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runFree()}
            placeholder="e.g. Sort the returned packages, then inspect aisle C for hazards"
            className="flex-1 rounded-xl border border-white/10 bg-black/30 px-4 py-3.5 text-[15px] text-fg outline-none transition-colors placeholder:text-faint focus:border-cyan/60"
          />
          <Button variant="primary" className="px-6 py-3.5" onClick={runFree}>
            <SendHorizontal size={17} />
            Run task
          </Button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="glass-tint rounded-full px-3 py-1.5 text-xs text-dim transition-colors hover:text-fg"
            >
              {s}
            </button>
          ))}
        </div>
      </GlassCard>

      {/* missions */}
      <div>
        <div className="mb-3 px-1">
          <Kicker>dispatch a mission</Kicker>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <MissionCard
            icon={<PackageSearch size={20} />}
            title="Sort package returns"
            desc="Drive to the returns area and sort returned packages onto the correct racks."
            cta="Start sorting"
            accent="linear-gradient(135deg,#22d3ee,#3b82f6)"
            onRun={() => send(PROMPTS.sort)}
          />
          <MissionCard
            icon={<Brush size={20} />}
            title="Housekeeping"
            desc="Tidy a single rack — the robot returns stray items to their slots."
            cta="Tidy next rack"
            accent="linear-gradient(135deg,#a78bfa,#6366f1)"
            extra={
              <p className="mb-4 text-sm text-dim">
                Next rack: <span className="font-mono text-fg">{RACKS[rackIdx]}</span>
              </p>
            }
            onRun={() => {
              send(PROMPTS.housekeepRack + RACKS[rackIdx]);
              setRackIdx((i) => (i + 1) % RACKS.length);
            }}
          />
          <MissionCard
            icon={<ShieldAlert size={20} />}
            title="Inspect for hazards"
            desc="Patrol with the VLM and report spills, blockages and anomalies on the Mission tab."
            cta="Begin inspection"
            accent="linear-gradient(135deg,#fbbf24,#f97316)"
            onRun={() => send(PROMPTS.inspect)}
          />
        </div>
      </div>

      {/* scenarios */}
      <div>
        <div className="mb-3 px-1">
          <Kicker>stage the warehouse</Kicker>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <ScenarioTile icon={<Boxes size={18} />} title="Standard" desc="Returns to sort and routine housekeeping." svc="standard" accent="#22d3ee" />
          <ScenarioTile icon={<Brush size={18} />} title="Housekeeping" desc="Items left out of place across racks." svc="housekeep" accent="#a78bfa" />
          <ScenarioTile icon={<TriangleAlert size={18} />} title="Anomalies" desc="Spills, blocked paths and hazards." svc="anomalies" accent="#fbbf24" />
          <ScenarioTile icon={<Eraser size={18} />} title="Cleanup" desc="Reset to an empty, ordered warehouse." svc="cleanup" accent="#34d399" />
        </div>
        <div className="mt-2 px-1">
          <Button variant="subtle" className="px-1 text-xs" onClick={() => callService("restart")}>
            Restart orchestrator
          </Button>
        </div>
      </div>

      {/* shipment + manual */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[2fr_1fr]">
        <GlassCard title="Prepare a shipment" icon={<PackageCheck size={14} />}>
          <p className="mb-3 text-sm text-dim">Select items to pick, pack and stage for shipping.</p>
          <div className="mb-4 flex flex-wrap gap-2">
            {SHIPMENT_ITEMS.map((it) => {
              const on = !!items[it];
              return (
                <button
                  key={it}
                  onClick={() => setItems((s) => ({ ...s, [it]: !on }))}
                  className={cn(
                    "rounded-full px-3.5 py-2 text-sm transition-all",
                    on ? "bg-gradient-to-r from-cyan to-blue text-[#04121a]" : "glass-tint text-dim hover:text-fg",
                  )}
                >
                  {it}
                </button>
              );
            })}
          </div>
          <Button
            variant="primary"
            onClick={() => send(PROMPTS.shipment + SHIPMENT_ITEMS.filter((i) => items[i]).join(", "))}
          >
            <PackageCheck size={16} />
            Prepare shipment
          </Button>
        </GlassCard>

        <GlassCard title="Manual drive">
          <div className="grid place-items-center py-2">
            <div className="grid grid-cols-3 gap-2">
              <span />
              <DpadButton icon={<ArrowUp size={20} />} onDown={() => teleop(0.5, 0)} onUp={() => teleop(0, 0)} />
              <span />
              <DpadButton icon={<ArrowLeft size={20} />} onDown={() => teleop(0, 0.5)} onUp={() => teleop(0, 0)} />
              <div className="grid h-14 w-14 place-items-center rounded-2xl bg-white/[0.03] text-faint ring-1 ring-white/8">
                <span className="h-2 w-2 rounded-full bg-white/30" />
              </div>
              <DpadButton icon={<ArrowRight size={20} />} onDown={() => teleop(0, -0.5)} onUp={() => teleop(0, 0)} />
              <span />
              <DpadButton icon={<ArrowDown size={20} />} onDown={() => teleop(-0.5, 0)} onUp={() => teleop(0, 0)} />
              <span />
            </div>
          </div>
          <p className="mt-1 text-center text-xs text-faint">hold to jog · /cmd_vel</p>
        </GlassCard>
      </div>
    </div>
  );
}

function DpadButton({ icon, onDown, onUp }: { icon: ReactNode; onDown: () => void; onUp: () => void }) {
  return (
    <button
      className="grid h-14 w-14 place-items-center rounded-2xl glass-tint text-fg transition-all hover:border-cyan/40 hover:text-cyan active:scale-95 active:bg-cyan/15"
      onMouseDown={onDown}
      onMouseUp={onUp}
      onMouseLeave={onUp}
      onTouchStart={(e) => {
        e.preventDefault();
        onDown();
      }}
      onTouchEnd={onUp}
    >
      {icon}
    </button>
  );
}
