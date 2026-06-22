import type { ButtonHTMLAttributes, ReactNode } from "react";
import { useId } from "react";
import { cn } from "../lib/cn";

/* ============================================================ primitives === */

export function Kicker({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("kicker", className)}>{children}</span>;
}

export function GlassCard({
  title,
  icon,
  right,
  className,
  bodyClassName,
  children,
  glow,
}: {
  title?: string;
  icon?: ReactNode;
  right?: ReactNode;
  className?: string;
  bodyClassName?: string;
  children?: ReactNode;
  glow?: boolean;
}) {
  return (
    <section className={cn("glass relative overflow-hidden rounded-2xl p-5", glow && "glow-cyan", className)}>
      {(title || right) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            {icon && <span className="text-cyan/90">{icon}</span>}
            {title && <Kicker>{title}</Kicker>}
          </div>
          {right}
        </header>
      )}
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

/* --------------------------------------------------------------- Button --- */
type Variant = "primary" | "danger" | "ghost" | "subtle";

const variants: Record<Variant, string> = {
  primary:
    "text-[#04121a] font-semibold bg-gradient-to-r from-cyan to-blue hover:brightness-110 " +
    "shadow-[0_8px_30px_-10px_rgba(34,211,238,0.7)]",
  danger:
    "text-white font-semibold bg-gradient-to-r from-red to-rose hover:brightness-110 " +
    "shadow-[0_8px_30px_-10px_rgba(251,90,90,0.8)]",
  ghost: "glass-tint text-fg hover:border-white/20 hover:bg-white/[0.07]",
  subtle: "text-dim hover:text-fg",
};

export function Button({
  variant = "ghost",
  className,
  children,
  ...props
}: { variant?: Variant } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm",
        "cursor-pointer select-none transition-all duration-200 active:scale-[0.98]",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan/70",
        "disabled:opacity-50 disabled:active:scale-100",
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

/* ------------------------------------------------------------ StatusOrb --- */
export type OrbState = "ok" | "warn" | "bad" | "idle" | "busy";

const orbColor: Record<OrbState, string> = {
  ok: "var(--color-emerald)",
  warn: "var(--color-amber)",
  bad: "var(--color-red)",
  idle: "#64748b",
  busy: "var(--color-cyan)",
};

export function StatusOrb({ state, pulse }: { state: OrbState; pulse?: boolean }) {
  const c = orbColor[state];
  return (
    <span className="relative inline-flex h-2.5 w-2.5 shrink-0 items-center justify-center">
      {pulse && (
        <span
          className="absolute inline-flex h-2.5 w-2.5 rounded-full"
          style={{ background: c, animation: "orb-pulse 1.8s ease-out infinite" }}
        />
      )}
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full" style={{ background: c, boxShadow: `0 0 10px ${c}` }} />
    </span>
  );
}

export function Chip({
  state,
  children,
  pulse,
}: {
  state: OrbState;
  children: ReactNode;
  pulse?: boolean;
}) {
  return (
    <span className="glass-tint inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs text-dim">
      <StatusOrb state={state} pulse={pulse} />
      {children}
    </span>
  );
}

/* ---------------------------------------------------------- RadialGauge --- */
const accents: Record<string, [string, string]> = {
  cyan: ["#22d3ee", "#3b82f6"],
  violet: ["#a78bfa", "#6366f1"],
  amber: ["#fbbf24", "#f97316"],
  emerald: ["#34d399", "#10b981"],
  rose: ["#fb7185", "#ef4444"],
};

export function RadialGauge({
  value,
  label,
  unit = "%",
  accent = "cyan",
  size = 132,
}: {
  value?: number;
  label: string;
  unit?: string;
  accent?: keyof typeof accents;
  size?: number;
}) {
  const id = useId();
  const has = value !== undefined && Number.isFinite(value);
  const v = Math.max(0, Math.min(100, value ?? 0));
  const stroke = 9;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const [from, to] = accents[accent];

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <defs>
            <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor={from} />
              <stop offset="100%" stopColor={to} />
            </linearGradient>
          </defs>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={stroke} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={`url(#${id})`}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={has ? c * (1 - v / 100) : c}
            style={{ transition: "stroke-dashoffset 0.7s cubic-bezier(0.22,1,0.36,1)", filter: `drop-shadow(0 0 6px ${from}88)` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-3xl font-semibold tnum text-fg">{has ? Math.round(v) : "—"}</span>
          <span className="text-xs text-faint">{unit}</span>
        </div>
      </div>
      <span className="kicker">{label}</span>
    </div>
  );
}

/* --------------------------------------------------------------- Meter --- */
export function Meter({
  value,
  accent = "cyan",
  label,
  valueText,
}: {
  value?: number;
  accent?: keyof typeof accents;
  label?: string;
  valueText?: string;
}) {
  const has = value !== undefined && Number.isFinite(value);
  const v = Math.max(0, Math.min(100, value ?? 0));
  const [from, to] = accents[accent];
  return (
    <div className="w-full">
      {(label || valueText) && (
        <div className="mb-1.5 flex items-baseline justify-between">
          {label && <span className="text-sm text-dim">{label}</span>}
          <span className="font-mono text-sm tnum text-fg">{valueText ?? (has ? `${Math.round(v)}%` : "—")}</span>
        </div>
      )}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/8">
        <div
          className="h-full rounded-full"
          style={{
            width: has ? `${Math.max(2, v)}%` : "0%",
            background: `linear-gradient(90deg, ${from}, ${to})`,
            boxShadow: `0 0 12px ${from}aa`,
            transition: "width 0.6s cubic-bezier(0.22,1,0.36,1)",
          }}
        />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ Sparkline --- */
export function Sparkline({
  data,
  accent = "cyan",
  width = 120,
  height = 34,
}: {
  data: number[];
  accent?: keyof typeof accents;
  width?: number;
  height?: number;
}) {
  const id = useId();
  const [from] = accents[accent];
  if (data.length < 2) return <svg width={width} height={height} />;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - 3 - ((d - min) / span) * (height - 6);
    return [x, y] as const;
  });
  const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} ${width},${height} 0,${height}`;
  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={from} stopOpacity="0.35" />
          <stop offset="100%" stopColor={from} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#${id})`} />
      <polyline points={line} fill="none" stroke={from} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="2.4" fill={from} />
    </svg>
  );
}

/* ---------------------------------------------------------------- Stat --- */
export function Stat({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  accent?: string;
}) {
  return (
    <div className="glass-tint rounded-xl px-4 py-3">
      <div className="kicker mb-1">{label}</div>
      <div className="font-display text-2xl font-semibold leading-none tnum" style={accent ? { color: accent } : undefined}>
        {value}
      </div>
      {hint && <div className="mt-1.5 text-xs text-faint">{hint}</div>}
    </div>
  );
}

/* -------------------------------------------------------------- KeyRow --- */
export function KeyRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 text-sm">
      <span className="text-dim">{label}</span>
      <span className="font-mono tnum text-fg/90">{value}</span>
    </div>
  );
}
