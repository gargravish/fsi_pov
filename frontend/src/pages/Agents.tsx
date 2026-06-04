import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { api } from "../lib/api";
import { Card, SectionTitle, Badge, fmtUsd } from "../components/ui";
import { PersonaEvent } from "../lib/types";
import ForecastChart from "../components/ForecastChart";
import {
  Database, Workflow, FlaskConical, MessagesSquare, Briefcase,
  Loader2, CheckCircle2, ArrowDown, ExternalLink, Circle, Send, MessageSquareWarning,
} from "lucide-react";

const GOALS = [
  "Build behavioural segments and name them",
  "Which UHNW clients will we lose next quarter, and why?",
  "Forecast net new money for APAC over the next year",
];

const ORDER = ["raw", "de", "ds", "ca", "business"] as const;
type Pid = (typeof ORDER)[number];

const META: Record<string, { icon: any; title: string; subtitle: string; color: string }> = {
  raw: { icon: Database, title: "Raw Data", subtitle: "Two banks · fragmented sources", color: "#64748b" },
  de: { icon: Workflow, title: "Data Engineering Agent", subtitle: "Google Cloud · A2A · Dataform", color: "#38bdf8" },
  ds: { icon: FlaskConical, title: "Data Scientist", subtitle: "BigQuery ML · TimesFM · BigFrames", color: "#22c55e" },
  ca: { icon: MessagesSquare, title: "Conversational Analytics Agent", subtitle: "Gemini Data Analytics", color: "#a855f7" },
  business: { icon: Briefcase, title: "Business User", subtitle: "Decision & action", color: "#f59e0b" },
};

interface Block { status: "idle" | "working" | "done" | "needs_input"; badge?: string; purpose?: string; output?: any; }

export default function Agents() {
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState(false);
  const [blocks, setBlocks] = useState<Record<string, Block>>({});

  function applyEvent(e: PersonaEvent) {
    if (e.type !== "persona" || !e.id) return;
    setBlocks((prev) => ({
      ...prev,
      [e.id!]: { status: e.status as any, badge: e.badge, purpose: e.purpose,
                 output: e.output ?? prev[e.id!]?.output },
    }));
  }

  async function run(g: string) {
    if (!g.trim() || busy) return;
    setGoal(g); setBusy(true);
    setBlocks(Object.fromEntries(ORDER.map((id) => [id, { status: "idle" }])));
    await api.agents(g, applyEvent);
    setBusy(false);
  }

  // human-in-the-loop: send the user's reply to a paused CA conversation
  async function sendReply(convToken: string, reply: string) {
    setBusy(true);
    await api.agentsCaReply(convToken, reply, applyEvent);
    setBusy(false);
  }

  return (
    <div className="space-y-6">
      <SectionTitle kicker="ADK · Agent-to-Agent (A2A) · Data lifecycle" title="Agent Console"
        sub="Watch a business goal flow across the data lifecycle — raw two-bank data, the real Google Cloud Data Engineering Agent, a BigQuery-ML Data Scientist, the live Conversational Analytics agent, and the business user — each persona producing real output as the agents coordinate." />

      <Card>
        <div className="flex gap-2">
          <input className="input" placeholder="Set a business goal…" value={goal}
            onChange={(e) => setGoal(e.target.value)} onKeyDown={(e) => e.key === "Enter" && run(goal)} />
          <button className="btn" disabled={busy} onClick={() => run(goal)}>
            {busy ? <Loader2 size={15} className="animate-spin" /> : null} Run
          </button>
        </div>
        <div className="flex gap-2 flex-wrap mt-3">
          {GOALS.map((g) => <button key={g} className="chip hover:text-white" onClick={() => run(g)}>{g}</button>)}
        </div>
      </Card>

      {Object.keys(blocks).length === 0 && (
        <div className="text-muted text-sm py-10 text-center">Set a goal to watch the personas coordinate across the data lifecycle.</div>
      )}

      <div className="space-y-2">
        {ORDER.map((id, i) => (
          <div key={id}>
            <PersonaBlock id={id} block={blocks[id] ?? { status: "idle" }} busy={busy} onReply={sendReply} />
            {i < ORDER.length - 1 && (
              <div className="flex justify-center py-1">
                <ArrowDown size={16} className={blocks[id]?.status === "done" ? "text-accent2" : "text-edge"} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function PersonaBlock({ id, block, busy, onReply }:
  { id: Pid; block: Block; busy: boolean; onReply: (token: string, reply: string) => void }) {
  const m = META[id];
  const Icon = m.icon;
  const active = block.status !== "idle";
  const needsInput = block.status === "needs_input";
  return (
    <Card className={`transition ${active ? "" : "opacity-50"} ${needsInput ? "border-amber-500/60" : ""}`}>
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl grid place-items-center shrink-0"
          style={{ background: `${m.color}22`, border: `1px solid ${m.color}55` }}>
          <Icon size={18} style={{ color: m.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-white font-semibold">{m.title}</span>
            {block.badge && <Badge tone={id === "de" || id === "ca" ? "green" : "default"}>
              {(id === "de" || id === "ca") ? "● " : ""}{block.badge}
            </Badge>}
            {needsInput && <Badge tone="amber">needs your input</Badge>}
          </div>
          <div className="text-xs text-muted">{block.purpose || m.subtitle}</div>
        </div>
        <div className="shrink-0">
          {block.status === "working" && <Loader2 size={18} className="animate-spin text-accent2" />}
          {block.status === "done" && <CheckCircle2 size={18} className="text-emerald-400" />}
          {needsInput && <MessageSquareWarning size={18} className="text-amber-400" />}
          {block.status === "idle" && <Circle size={18} className="text-edge" />}
        </div>
      </div>

      {block.output && (
        <div className="mt-4">
          <OutputView output={block.output} />
        </div>
      )}
      {needsInput && block.output?.conv_token && (
        <ReplyBox busy={busy} onSend={(text) => onReply(block.output.conv_token, text)} />
      )}
      {block.status === "working" && !block.output && (
        <div className="mt-3 text-xs text-muted italic">working…</div>
      )}
    </Card>
  );
}

function ReplyBox({ busy, onSend }: { busy: boolean; onSend: (text: string) => void }) {
  const [v, setV] = useState("");
  const send = () => { if (v.trim() && !busy) { onSend(v.trim()); setV(""); } };
  return (
    <div className="mt-3 rounded-xl border border-amber-500/40 bg-amber-500/5 p-2.5">
      <div className="text-[11px] text-amber-300/90 mb-1.5">The agent needs a clarification — reply to continue (human-in-the-loop):</div>
      <div className="flex gap-2">
        <input className="input" placeholder="Type your answer…" value={v}
          onChange={(e) => setV(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} disabled={busy} />
        <button className="btn" onClick={send} disabled={busy || !v.trim()}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
        </button>
      </div>
    </div>
  );
}

function Artifacts({ items }: { items: any[] }) {
  if (!items?.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {items.map((a, i) => (
        <a key={i} href={a.url} target="_blank" rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg bg-ink border border-edge hover:border-accent2 transition">
          <Database size={11} className="text-accent2" /> {a.label}
          <ExternalLink size={10} className="text-muted" />
        </a>
      ))}
    </div>
  );
}

function MiniTable({ columns, rows }: { columns: string[]; rows: any[] }) {
  const fmt = (v: any) => (typeof v === "number" ? new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(v) : v == null ? "—" : String(v));
  return (
    <div className="overflow-auto rounded-lg border border-edge">
      <table className="w-full text-xs">
        <thead><tr className="text-muted bg-panel2/50 text-left">{columns.map((c) => <th key={c} className="py-1.5 px-2 font-medium">{c}</th>)}</tr></thead>
        <tbody>{rows.map((r, ri) => (
          <tr key={ri} className="border-t border-edge">
            {(Array.isArray(r) ? r : columns.map((c) => r[c])).map((cell: any, ci: number) => <td key={ci} className="py-1.5 px-2 text-slate-200 font-mono">{fmt(cell)}</td>)}
          </tr>))}</tbody>
      </table>
    </div>
  );
}

function OutputView({ output }: { output: any }) {
  const k = output.kind;

  if (k === "raw")
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {output.sources?.map((s: any, i: number) => (
            <div key={i} className="p-2.5 rounded-lg bg-panel2/50 border border-edge">
              <div className="text-xs text-muted">{s.name}</div>
              <div className="text-lg font-bold text-white">{s.rows?.toLocaleString()}</div>
            </div>
          ))}
        </div>
        <div className="text-xs text-muted">Dual-banked clients discovered (entity resolution): <span className="text-white font-semibold">{output.dual_banked?.toLocaleString()}</span></div>
        {output.sample?.length > 0 && <MiniTable columns={["client_id", "full_name", "segment_tier", "source_banks", "dual_banked"]} rows={output.sample} />}
      </div>
    );

  if (k === "messages")
    return (
      <div className="space-y-2">
        {output.messages?.map((mm: string, i: number) => (
          <div key={i} className="text-sm text-slate-200 bg-panel2/40 rounded-lg px-3 py-2 [&_code]:bg-ink [&_code]:px-1 [&_code]:rounded">
            <ReactMarkdown>{mm}</ReactMarkdown>
          </div>
        ))}
        {output.workspace_url && (
          <a href={output.workspace_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg bg-ink border border-edge hover:border-accent2">
            <Workflow size={11} className="text-accent2" /> Open Dataform workspace <ExternalLink size={10} className="text-muted" />
          </a>
        )}
      </div>
    );

  if (k === "segments")
    return (
      <div>
        {output.headline && <p className="text-sm text-muted mb-2">{output.headline}</p>}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          {output.segments?.map((s: any) => (
            <div key={s.id} className="p-2.5 rounded-lg bg-panel2/50 border border-edge">
              <div className="text-sm font-semibold text-white leading-tight">{s.label}</div>
              <div className="text-[11px] text-muted mt-1">{s.size?.toLocaleString()} · {fmtUsd(s.avg_aum_usd)}</div>
              <Badge tone="blue">{s.dominant_asset}</Badge>
            </div>
          ))}
        </div>
        <Artifacts items={output.artifacts} />
      </div>
    );

  if (k === "forecast")
    return (
      <div>
        {output.headline && <p className="text-sm text-muted mb-2">{output.headline}</p>}
        <ForecastChart data={output.forecast} />
        <p className="text-xs text-muted mt-2">{output.forecast?.commentary}</p>
        <Artifacts items={output.artifacts} />
      </div>
    );

  if (k === "retention")
    return (
      <div>
        {output.headline && <p className="text-sm text-muted mb-2">{output.headline}</p>}
        <div className="space-y-1.5">
          {output.scores?.map((s: any) => (
            <div key={s.client_id} className="flex items-center gap-2 p-2 rounded-lg bg-panel2/50 border border-edge">
              <div className="flex-1 min-w-0">
                <div className="text-sm text-white truncate">{s.full_name} <span className="text-muted text-xs">· {s.segment_tier}</span></div>
                <div className="text-[11px] text-muted truncate">{s.drivers?.join(" · ")}</div>
              </div>
              <Badge tone={s.flight_risk > 0.6 ? "red" : "amber"}>{(s.flight_risk * 100).toFixed(0)}%</Badge>
            </div>
          ))}
        </div>
        <Artifacts items={output.artifacts} />
      </div>
    );

  if (k === "nba")
    return (
      <div>
        {output.headline && <p className="text-sm text-muted mb-2">{output.headline}</p>}
        <div className="space-y-1.5">
          {output.nba?.actions?.map((a: any, i: number) => (
            <div key={i} className="p-2.5 rounded-lg bg-panel2/50 border border-edge">
              <div className="flex items-center justify-between"><span className="text-sm text-white">{a.product}</span><Badge tone="green">{(a.score * 100).toFixed(0)}%</Badge></div>
              <p className="text-[11px] text-muted mt-1">{a.rationale}</p>
            </div>
          ))}
        </div>
        <Artifacts items={output.artifacts} />
      </div>
    );

  if (k === "ca")
    return (
      <div className="space-y-2">
        <div className="text-xs text-accent2 italic">“{output.question}”</div>
        {output.blocks?.map((b: any, i: number) => {
          if (b.type === "text") return <div key={i} className="text-sm text-slate-200 [&_strong]:font-semibold"><ReactMarkdown>{b.text}</ReactMarkdown></div>;
          if (b.type === "table") return <MiniTable key={i} columns={b.columns} rows={b.rows} />;
          if (b.type === "sql") return (
            <details key={i} className="bg-ink border border-edge rounded-lg p-2">
              <summary className="cursor-pointer text-[11px] text-accent2">Show SQL</summary>
              <pre className="text-[10px] text-slate-300 mt-1 overflow-auto whitespace-pre-wrap">{b.sql}</pre>
            </details>
          );
          return null;
        })}
      </div>
    );

  if (k === "text")
    return <div className="text-sm text-slate-100 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2.5 [&_strong]:font-semibold"><ReactMarkdown>{output.text}</ReactMarkdown></div>;

  return null;
}
