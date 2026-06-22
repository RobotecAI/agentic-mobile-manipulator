import { useState } from "react";
import { motion } from "motion/react";
import { Gamepad2, Radar, Activity } from "lucide-react";
import { Header } from "./components/Header";
import { ControlTab } from "./tabs/ControlTab";
import { StatusTab } from "./tabs/StatusTab";
import { MissionTab } from "./tabs/MissionTab";
import { cn } from "./lib/cn";

const TABS = [
  { id: "mission", label: "Mission", icon: Radar, el: <MissionTab /> },
  { id: "control", label: "Control", icon: Gamepad2, el: <ControlTab /> },
  { id: "status", label: "Telemetry", icon: Activity, el: <StatusTab /> },
] as const;

export default function App() {
  const initial = new URLSearchParams(window.location.search).get("tab") ?? "mission";
  const [active, setActive] = useState(TABS.find((t) => t.id === initial)?.id ?? "mission");
  const current = TABS.find((t) => t.id === active) ?? TABS[0];

  return (
    <div className="app-bg flex h-full flex-col">
      <Header />

      <div className="flex shrink-0 justify-center px-6 pt-5">
        <nav className="glass inline-flex items-center gap-1 rounded-2xl p-1.5">
          {TABS.map((t) => {
            const on = active === t.id;
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setActive(t.id)}
                className={cn(
                  "relative flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm transition-colors",
                  on ? "text-[#04121a]" : "text-dim hover:text-fg",
                )}
              >
                {on && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan to-blue shadow-[0_8px_30px_-10px_rgba(34,211,238,0.8)]"
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                )}
                <Icon size={16} className="relative z-10" />
                <span className="relative z-10 font-medium">{t.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      <main className="min-h-0 flex-1 overflow-y-auto px-6 py-5">{current.el}</main>
    </div>
  );
}
