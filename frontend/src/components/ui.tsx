import { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`card p-5 ${className}`}>{children}</div>;
}

export function SectionTitle({ kicker, title, sub }: { kicker?: string; title: string; sub?: string }) {
  return (
    <div className="mb-5">
      {kicker && <div className="text-accent2 text-xs font-semibold tracking-widest uppercase mb-1">{kicker}</div>}
      <h1 className="text-2xl font-bold text-white">{title}</h1>
      {sub && <p className="text-muted mt-1 max-w-3xl">{sub}</p>}
    </div>
  );
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: string }) {
  return (
    <div className="card p-4">
      <div className="text-muted text-xs font-medium">{label}</div>
      <div className="text-2xl font-bold text-white mt-1">{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  );
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "red" | "blue" | "green" | "amber" }) {
  const tones: Record<string, string> = {
    default: "bg-panel2 border-edge text-muted",
    red: "bg-accent/15 border-accent/40 text-red-300",
    blue: "bg-accent2/15 border-accent2/40 text-sky-300",
    green: "bg-emerald-500/15 border-emerald-500/40 text-emerald-300",
    amber: "bg-amber-500/15 border-amber-500/40 text-amber-300",
  };
  return <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border ${tones[tone]}`}>{children}</span>;
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="flex items-center gap-3 text-muted text-sm py-8 justify-center">
    <span className="h-2 w-2 rounded-full bg-accent2 animate-ping" /> {label}
  </div>;
}

/** Provenance badge — shows whether a client came from UBS, Credit Suisse, or both. */
export function SourceBadge({ source_banks, dual_banked }: { source_banks?: string; dual_banked?: boolean }) {
  const dual = dual_banked ?? (source_banks ?? "").includes("|");
  if (dual) return <Badge tone="red">UBS + CS</Badge>;
  if ((source_banks ?? "").includes("credit_suisse")) return <Badge tone="default">Credit Suisse</Badge>;
  return <Badge tone="blue">UBS</Badge>;
}

export function fmtUsd(n: number): string {
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}bn`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}m`;
  if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}k`;
  return `$${n.toFixed(0)}`;
}
export function fmtNum(n: number): string {
  return n.toLocaleString("en-US");
}
