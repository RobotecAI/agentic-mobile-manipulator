import { useState } from "react";
import { Bot, Camera, Eye, Map as MapIcon, RotateCcw, Sparkles, Terminal } from "lucide-react";
import { useRos, useTopic, useTopicLog } from "../ros/RosProvider";
import type { HRIMessage, StringMsg, VlmDescription } from "../ros/types";
import { CAMERAS } from "../ros/config";
import { parseRosList } from "../lib/parse";
import { useAlive } from "../lib/hooks";
import { Button, Chip, GlassCard, Kicker, Stat, StatusOrb } from "../components/ui";
import { CameraView } from "../components/CameraView";
import { MapCanvas } from "../components/MapCanvas";
import { cn } from "../lib/cn";

const SOURCE_GRADIENT: Record<string, string> = {
  Inspection: "linear-gradient(90deg,#fbbf24,#f97316)",
  Safety: "linear-gradient(90deg,#38bdf8,#6366f1)",
};

export function MissionTab() {
  const { callService } = useRos();
  const currentTask = useTopic<StringMsg>("currentTask");
  const currentAction = useTopic<HRIMessage>("currentAction");
  const actionBusy = useAlive(currentAction, 9000);
  const pastSteps = useTopic<StringMsg>("pastSteps");
  const taskQueue = useTopic<StringMsg>("taskQueue");
  const vlm = useTopicLog<VlmDescription>("vlm", 12);
  const [baseCam, setBaseCam] = useState<"base" | "wrist">("base");

  const taskText = currentTask?.data || "";
  const steps = parseRosList(pastSteps?.data);
  const queue = parseRosList(taskQueue?.data);

  return (
    <div className="mx-auto flex max-w-[1700px] flex-col gap-5">
      {/* mission status strip */}
      <GlassCard
        title="COGFRAME · v1.2 · drive telemetry"
        icon={<Sparkles size={14} />}
        right={
          <Button variant="ghost" onClick={() => callService("restart")}>
            <RotateCcw size={15} />
            Reset scene
          </Button>
        }
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <Stat label="Drive" value={<span className="text-emerald">IDLE</span>} />
          <Stat label="Task" value={<span className="truncate text-xl">{taskText ? taskText.slice(0, 14) : "—"}</span>} />
          <Stat label="Iter" value="0 / 0" />
          <Stat label="Phase" value="—" />
          <Stat label="Elapsed" value="00:00" />
          <Stat label="Drift" value="0" accent="var(--color-emerald)" />
        </div>
      </GlassCard>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.55fr_1fr]">
        {/* viewport */}
        <div className="flex flex-col gap-5">
          <GlassCard title="Live viewport" icon={<MapIcon size={14} />}>
            <div className="relative h-[400px] w-full">
              <MapCanvas />
              <div className="pointer-events-none absolute left-3 top-3 flex flex-col gap-2">
                <Chip state="busy" pulse>
                  autonomous nav
                </Chip>
              </div>
              <div className="pointer-events-none absolute right-3 top-3">
                <Kicker>occupancy + plan</Kicker>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <Kicker>{baseCam === "base" ? "base camera" : "wrist camera"}</Kicker>
                  <div className="flex gap-1">
                    {(["base", "wrist"] as const).map((c, i) => (
                      <button
                        key={c}
                        onClick={() => setBaseCam(c)}
                        className={cn(
                          "h-6 w-7 rounded-md text-xs font-medium transition-all",
                          baseCam === c
                            ? "bg-gradient-to-r from-cyan to-blue text-[#04121a]"
                            : "glass-tint text-dim hover:text-fg",
                        )}
                      >
                        {i + 1}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="aspect-video">
                  <CameraView topic={CAMERAS[baseCam]} />
                </div>
              </div>
              <div>
                <div className="mb-2 flex items-center gap-2">
                  <Camera size={13} className="text-faint" />
                  <Kicker>top view</Kicker>
                </div>
                <div className="aspect-video">
                  <CameraView topic={CAMERAS.top} />
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* agent + vlm */}
        <div className="flex flex-col gap-5">
          <GlassCard title="Agent" icon={<Bot size={14} />}>
            <div className="mb-1">
              <Kicker>current task</Kicker>
            </div>
            <p className="mb-4 font-display text-lg leading-snug text-fg">{taskText || "Awaiting dispatch…"}</p>

            <div className="mb-4 rounded-xl border border-white/8 bg-white/[0.03] p-3">
              <div className="mb-1.5 flex items-center gap-2">
                <StatusOrb state={actionBusy ? "busy" : "idle"} pulse={actionBusy} />
                <Kicker>current action</Kicker>
              </div>
              <p className="font-mono text-[13px] leading-relaxed text-cyan/90">
                {currentAction?.text || "idle"}
              </p>
            </div>

            <div className="mb-2">
              <Kicker>plan &amp; history</Kicker>
            </div>
            <div className="relative max-h-60 space-y-0 overflow-y-auto pl-1">
              {steps.length === 0 && queue.length === 0 && <p className="py-2 text-sm text-faint">No steps yet.</p>}
              {steps.map((s, i) => (
                <TimelineRow key={`p${i}`} text={s} done />
              ))}
              {queue.map((s, i) => (
                <TimelineRow key={`q${i}`} text={s} active={i === 0} />
              ))}
            </div>
          </GlassCard>

          <GlassCard
            title="VLM stream"
            icon={<Eye size={14} />}
            right={<span className="font-mono text-xs text-faint">{vlm.length} frames</span>}
          >
            <div className="mb-3 grid grid-cols-4 gap-2">
              <Stat label="Drives" value="0" />
              <Stat label="Success" value="—" />
              <Stat label="Drift" value="—" />
              <Stat label="Dur" value="—" />
            </div>
            <div className="max-h-72 space-y-2.5 overflow-y-auto pr-1">
              {vlm.length === 0 && (
                <p className="flex items-center gap-2 py-2 text-sm text-faint">
                  <Terminal size={14} /> waiting for /vlm_topic…
                </p>
              )}
              {vlm.map((v, i) => (
                <div key={i} className="rounded-xl border border-white/8 bg-white/[0.025] p-3">
                  <span
                    className="mb-1.5 inline-block rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#04121a]"
                    style={{ background: SOURCE_GRADIENT[v.source] ?? "linear-gradient(90deg,#22d3ee,#a78bfa)" }}
                  >
                    {v.source || "vlm"}
                  </span>
                  <p className="text-[13px] leading-relaxed text-fg/90">{v.description}</p>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}

function TimelineRow({ text, done, active }: { text: string; done?: boolean; active?: boolean }) {
  return (
    <div className="flex gap-3 pb-3 last:pb-0">
      <div className="relative flex flex-col items-center">
        <span
          className={cn(
            "mt-1 h-2.5 w-2.5 shrink-0 rounded-full",
            done ? "bg-white/25" : active ? "bg-cyan shadow-[0_0_10px_#22d3ee]" : "bg-white/40",
          )}
        />
        <span className="mt-1 w-px flex-1 bg-white/10" />
      </div>
      <span className={cn("text-sm leading-snug", done ? "text-faint line-through" : active ? "text-fg" : "text-dim")}>
        {text}
      </span>
    </div>
  );
}
