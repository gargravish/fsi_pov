import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Area, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, ReferenceLine,
} from "recharts";
import {
  ArrowUpRight, ArrowDownRight, ChevronDown, Sparkles, Activity, Search, TrendingUp, ShieldCheck, Code2,
} from "lucide-react";
import { api } from "../lib/api";
import { Card, SectionTitle, Badge, Stat, Loading } from "../components/ui";
import type { KeyDriver, KeyDriversResult, DriverDrilldown } from "../lib/types";

const METRICS = [
  { id: "nna", label: "Net New Money" },
  { id: "inflow", label: "Gross Inflows" },
  { id: "outflow", label: "Gross Outflows" },
];

const fmtM = (n: number) => `${n < 0 ? "−" : ""}$${Math.abs(n).toLocaleString("en-US", { maximumFractionDigits: 0 })}m`;
const pct = (n: number) => `${n > 0 ? "+" : ""}${(n * 100).toFixed(1)}%`;
const md = (s: string) => s.replace(/\*\*(.+?)\*\*/g, "<strong class='text-white'>$1</strong>");

/** A move is "good" if it pushes the metric in its favourable direction. */
const isGood = (d: KeyDriver, favourable: "higher" | "lower") => (d.direction === "up") === (favourable === "higher");

function SegChips({ segment }: { segment: { name: string; value: string }[] }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 min-w-0">
      {segment.map((s, i) => (
        <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-panel2 border border-edge text-xs text-slate-200">
          <span className="text-muted">{s.name}:</span> {s.value}
        </span>
      ))}
    </div>
  );
}

function StageHeader({ icon: Icon, n, title, hint, fn }: { icon: any; n: number; title: string; hint: string; fn?: string }) {
  return (
    <div className="flex items-center gap-2 mb-2 flex-wrap">
      <span className="h-6 w-6 rounded-lg bg-accent2/15 border border-accent2/40 grid place-items-center text-accent2 text-xs font-bold">{n}</span>
      <Icon size={15} className="text-accent2" />
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <span className="text-xs text-muted">· {hint}</span>
      {fn && <span className="ml-1 px-2 py-0.5 rounded-md bg-accent2/15 border border-accent2/40 text-accent2 text-[11px] font-mono font-semibold">{fn}</span>}
    </div>
  );
}

/** Collapsible "view SQL" block showing the BigQuery AI statement behind a stage. */
function SqlBlock({ fn, sql }: { fn: string; sql: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3">
      <button onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[11px] text-muted hover:text-accent2 transition">
        <Code2 size={13} /> {open ? "Hide" : "View"} SQL · <span className="font-mono text-accent2">{fn}</span>
        <ChevronDown size={12} className={`transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <pre className="mt-2 p-3 rounded-lg bg-[#0a0f1d] border border-edge overflow-x-auto text-[11px] leading-relaxed text-slate-300 font-mono whitespace-pre">
          <code>{sql}</code>
        </pre>
      )}
    </div>
  );
}

/** The combined What-Happened → What's-Next timeline (history actual + forecast band). */
function Timeline({ dd }: { dd: DriverDrilldown }) {
  const lastActual = dd.what_happened.trend[dd.what_happened.trend.length - 1];
  const data = [
    ...dd.what_happened.trend.map((p) => ({ ts: p.ts, actual: p.value, anomaly: p.is_anomaly })),
    // bridge the gap so the forecast line connects to the last actual
    { ts: lastActual.ts, forecast: lastActual.value, band: [lastActual.value, lastActual.value] },
    ...dd.whats_next.forecast.map((p) => ({ ts: p.ts, forecast: p.yhat, band: [p.lo, p.hi] })),
  ];
  // red marker on months AI.DETECT_ANOMALIES flagged
  const dot = (props: any) => {
    const { cx, cy, payload } = props;
    if (cx == null || cy == null) return <g />;
    return payload?.anomaly
      ? <circle cx={cx} cy={cy} r={4} fill="#f43f5e" stroke="#0f1729" strokeWidth={1.5} />
      : <g />;
  };
  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#1e2a45" vertical={false} />
        <XAxis dataKey="ts" tick={{ fill: "#8aa0c0", fontSize: 10 }} interval="preserveStartEnd" />
        <YAxis tick={{ fill: "#8aa0c0", fontSize: 10 }} width={44} />
        <Tooltip contentStyle={{ background: "#0f1729", border: "1px solid #1e2a45", borderRadius: 12 }} />
        <ReferenceLine x={lastActual.ts} stroke="#475569" strokeDasharray="3 3" label={{ value: "now", fill: "#8aa0c0", fontSize: 10, position: "top" }} />
        <Area type="monotone" dataKey="band" stroke="none" fill="#38bdf8" fillOpacity={0.12} name="forecast range" />
        <Line type="monotone" dataKey="actual" stroke="#e2e8f0" strokeWidth={2} dot={dot} name="actual ($m/mo)" />
        <Line type="monotone" dataKey="forecast" stroke="#38bdf8" strokeWidth={2.5} strokeDasharray="5 4" dot={false} name="forecast ($m/mo)" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function DriverDeepDive({ metric, driver }: { metric: string; driver: KeyDriver }) {
  const { data: dd } = useQuery<DriverDrilldown>({
    queryKey: ["key-driver-drill", metric, driver.label],
    queryFn: () => api.keyDriverDrilldown(metric, driver.label, driver.segment),
  });
  if (!dd) return <div className="px-1 py-4"><Loading label="Running AI deep-dive (AI.DETECT_ANOMALIES + AI.KEY_DRIVERS)…" /></div>;

  const wh = dd.what_happened;
  const maxFactor = Math.max(...dd.rca.factors.map((f) => Math.abs(f.impact_usd_m)), 1);
  const good = (dd.direction === "up") === (metric !== "outflow");

  return (
    <div className="mt-3 mb-1 rounded-xl border border-edge bg-panel2/40 p-4 space-y-5">
      {/* 1 — What happened */}
      <section>
        <StageHeader icon={Activity} n={1} title="What happened" hint="anomaly detection on the trend" fn={wh.ai_function} />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
          <Stat label="Prior 6m" value={fmtM(wh.prior_usd_m)} />
          <Stat label="Recent 6m" value={fmtM(wh.recent_usd_m)} />
          <Stat label="Change" value={<span className={good ? "text-emerald-300" : "text-red-300"}>{fmtM(wh.difference_usd_m)} <span className="text-sm">({pct(wh.relative_difference)})</span></span>} />
          <Stat label="Unexpected vs trend" value={<span className={good ? "text-emerald-300" : "text-red-300"}>{fmtM(wh.unexpected_difference_usd_m)}</span>} sub={`contribution ${(wh.contribution * 100).toFixed(1)}% · size ${(wh.apriori_support * 100).toFixed(1)}%`} />
        </div>
        <Timeline dd={dd} />
        <p className="text-[11px] text-muted mt-1"><span className="text-rose-400">●</span> red markers = months flagged by AI.DETECT_ANOMALIES.</p>
        <SqlBlock fn={wh.ai_function} sql={wh.sql} />
      </section>

      {/* 2 — Why it happened (RCA) */}
      <section>
        <StageHeader icon={Search} n={2} title="Why it happened" hint="root-cause analysis" fn={dd.rca.ai_function} />
        <p className="text-sm text-slate-200 leading-relaxed mb-3" dangerouslySetInnerHTML={{ __html: md(dd.rca.narrative) }} />
        <div className="space-y-2">
          {dd.rca.factors.map((f, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="w-40 shrink-0 text-xs text-slate-200 font-medium pt-0.5">{f.factor}</div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 rounded-full bg-panel overflow-hidden">
                    <div className="h-full bg-accent2/70" style={{ width: `${Math.max(4, (Math.abs(f.impact_usd_m) / maxFactor) * 100)}%` }} />
                  </div>
                  <span className="text-xs text-muted w-16 text-right">{fmtM(f.impact_usd_m)}</span>
                </div>
                <div className="text-[11px] text-muted mt-0.5">{f.detail}</div>
              </div>
            </div>
          ))}
        </div>
        <SqlBlock fn={dd.rca.ai_function} sql={dd.rca.sql} />
      </section>

      {/* 3 — What's next (forecast) */}
      <section>
        <StageHeader icon={TrendingUp} n={3} title="What's next" hint="forward path · TimesFM 2.5" fn={dd.whats_next.ai_function} />
        <p className="text-sm text-slate-200 leading-relaxed" dangerouslySetInnerHTML={{ __html: md(dd.whats_next.commentary) }} />
        <p className="text-[11px] text-muted mt-1">Forecast is plotted as the dashed line + shaded range on the timeline above.</p>
        <SqlBlock fn={dd.whats_next.ai_function} sql={dd.whats_next.sql} />
      </section>

      {/* 4 — How to prevent it */}
      <section>
        <StageHeader icon={ShieldCheck} n={4} title={good ? "How to sustain it" : "How to prevent it"} hint="recommended actions" fn={dd.prevention.ai_function} />
        <div className="grid md:grid-cols-2 gap-2">
          {dd.prevention.actions.map((a, i) => (
            <div key={i} className="rounded-lg border border-edge bg-panel/60 p-3">
              <div className="flex items-center justify-between gap-2 mb-1">
                <div className="text-sm font-semibold text-white">{a.title}</div>
                <Badge tone="green">{a.owner}</Badge>
              </div>
              <div className="text-xs text-muted leading-relaxed">{a.detail}</div>
            </div>
          ))}
        </div>
        <SqlBlock fn={dd.prevention.ai_function} sql={dd.prevention.sql} />
      </section>
    </div>
  );
}

function DriverRow({ d, max, favourable, metric, open, onToggle }:
  { d: KeyDriver; max: number; favourable: "higher" | "lower"; metric: string; open: boolean; onToggle: () => void }) {
  const good = isGood(d, favourable);
  const tone = good ? "text-emerald-300" : "text-red-300";
  const bar = good ? "bg-emerald-500/70" : "bg-accent/70";
  const width = `${Math.max(4, (Math.abs(d.unexpected_difference_usd_m) / max) * 100)}%`;
  return (
    <div className="border-b border-edge/60 last:border-0">
      <button onClick={onToggle}
        className={`w-full text-left py-3 transition rounded-lg px-2 -mx-2 hover:bg-panel2/50 ${open ? "bg-panel2/40" : ""}`}>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 min-w-0">
            <ChevronDown size={15} className={`text-muted shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
            <SegChips segment={d.segment} />
          </div>
          <div className={`flex items-center gap-1 shrink-0 font-semibold text-sm ${tone}`}>
            {d.direction === "up" ? <ArrowUpRight size={15} /> : <ArrowDownRight size={15} />}
            {pct(d.relative_difference)}
          </div>
        </div>
        <div className="mt-2 flex items-center gap-3 pl-6">
          <div className="flex-1 h-2 rounded-full bg-panel2 overflow-hidden">
            <div className={`h-full ${bar}`} style={{ width }} />
          </div>
          <div className="text-xs text-muted shrink-0 w-44 text-right">
            unexpected <span className={`font-semibold ${tone}`}>{fmtM(d.unexpected_difference_usd_m)}</span>
          </div>
        </div>
        <div className="mt-1.5 pl-6 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-muted">
          <span>recent <span className="text-slate-300">{fmtM(d.metric_interest_usd_m)}</span></span>
          <span>prior <span className="text-slate-300">{fmtM(d.metric_reference_usd_m)}</span></span>
          <span>contribution <span className="text-slate-300">{(d.contribution * 100).toFixed(1)}%</span></span>
          <span>segment size <span className="text-slate-300">{(d.apriori_support * 100).toFixed(1)}%</span></span>
          <span className="text-accent2">{open ? "hide deep-dive" : "click to deep-dive →"}</span>
        </div>
      </button>
      {open && <DriverDeepDive metric={metric} driver={d} />}
    </div>
  );
}

export default function DriverLens() {
  const [metric, setMetric] = useState("nna");
  const [open, setOpen] = useState<string | null>(null);
  const { data } = useQuery<KeyDriversResult>({
    queryKey: ["key-drivers", metric],
    queryFn: () => api.keyDrivers(metric),
  });

  const maxUnexpected = data ? Math.max(...data.drivers.map((d) => Math.abs(d.unexpected_difference_usd_m)), 1) : 1;

  return (
    <div className="space-y-6">
      <SectionTitle kicker="AI.KEY_DRIVERS · BigQuery" title="Driver Lens"
        sub="From what to why. The Forecast Room shows where the numbers are heading; Driver Lens runs BigQuery's AI.KEY_DRIVERS to explain why a flow metric moved — ranking the client segments that most over- or under-shot the bankwide trend. Click any driver to deep-dive: what happened, why (RCA), what's next, and what to do about it." />

      <Card>
        <div className="flex flex-wrap items-center gap-2 mb-4">
          {METRICS.map((m) => (
            <button key={m.id} onClick={() => { setMetric(m.id); setOpen(null); }}
              className={metric === m.id ? "btn" : "btn-ghost"}>{m.label}</button>
          ))}
          <div className="flex-1" />
          {data && <Badge tone="blue">{data.reference_period} → {data.interest_period}</Badge>}
        </div>

        {!data ? <Loading label="Running AI.KEY_DRIVERS…" /> : (
          <>
            <div className="grid grid-cols-3 gap-3 mb-5">
              <Stat label={`${data.metric_label} · prior 6m`} value={fmtM(data.total_reference_usd_m)} />
              <Stat label={`${data.metric_label} · recent 6m`} value={fmtM(data.total_interest_usd_m)} />
              <Stat label="Net change"
                value={<span className={data.net_change_usd_m >= 0 ? "text-emerald-300" : "text-red-300"}>{fmtM(data.net_change_usd_m)}</span>}
                sub="across the top driver segments" />
            </div>

            <div className="text-xs text-muted mb-1">
              Ranked by <span className="text-slate-300">unexpected difference</span> — the part of the move that
              the bankwide trend does <i>not</i> explain. {data.direction === "lower"
                ? "For outflows, red bars are segments bleeding faster than expected."
                : "Green bars over-shot the trend; red bars dragged the metric down."}
            </div>
            <div>
              {data.drivers.map((d) => (
                <DriverRow key={d.label} d={d} max={maxUnexpected} favourable={data.direction}
                  metric={metric} open={open === d.label}
                  onToggle={() => setOpen(open === d.label ? null : d.label)} />
              ))}
            </div>

            <div className="mt-5 p-4 rounded-xl bg-panel2/50 border border-edge">
              <Badge tone="blue"><Sparkles size={12} /> AI commentary</Badge>
              <p className="text-sm text-slate-200 mt-2 leading-relaxed" dangerouslySetInnerHTML={{ __html: md(data.commentary) }} />
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
