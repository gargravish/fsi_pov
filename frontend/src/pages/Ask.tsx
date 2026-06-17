import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import vegaEmbed from "vega-embed";
import { api } from "../lib/api";
import { Card, SectionTitle } from "../components/ui";
import { AskBlock } from "../lib/types";
import { Send, Loader2, Sparkles } from "lucide-react";

const SUGGESTED = [
  "Which booking centre has the highest total AuM? Top 5.",
  "Compare discretionary vs advisory mandate AuM by region",
  "Average net new money per client by booking centre",
  "Top 5 advisors by assets under management",
];

export default function Ask() {
  const [q, setQ] = useState("");
  const [blocks, setBlocks] = useState<AskBlock[]>([]);
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  async function run(question: string) {
    if (!question.trim() || busy) return;
    setBlocks([]); setBusy(true); setQ(question);
    await api.ask(question, (b) => {
      if (b.type !== "done") setBlocks((prev) => [...prev, b]);
      setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }), 20);
    });
    setBusy(false);
  }

  // collapse consecutive thinking blocks: show only the latest few as a trail
  return (
    <div className="space-y-6">
      <SectionTitle kicker="Conversational Analytics API · live data agent" title="Ask Helix"
        sub="Any banker or executive can query the whole estate in plain English. The BigQuery Conversational Analytics data agent (FSI_POV) streams its reasoning, then returns text, tables, charts and the SQL it ran." />

      <Card>
        <div className="flex gap-2">
          <input className="input" placeholder="Ask anything about the estate…" value={q}
            onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && run(q)} />
          <button className="btn" disabled={busy} onClick={() => run(q)}>
            {busy ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />} Ask
          </button>
        </div>
        <div className="flex gap-2 flex-wrap mt-3">
          {SUGGESTED.map((s) => (
            <button key={s} className="chip hover:text-white" onClick={() => run(s)}>{s}</button>
          ))}
        </div>
      </Card>

      {(blocks.length > 0 || busy) && (
        <Card>
          <div ref={scrollRef} className="space-y-3 max-h-[60vh] overflow-y-auto">
            {blocks.map((b, i) => <BlockView key={i} block={b} />)}
            {busy && (
              <div className="flex items-center gap-2 text-sm text-accent2">
                <Loader2 size={14} className="animate-spin" /> the agent is working…
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

function BlockView({ block }: { block: AskBlock }) {
  if (block.type === "thinking")
    return (
      <div className="flex items-center gap-2 text-xs text-muted/90">
        <Sparkles size={12} className="text-accent2 shrink-0" />
        <span className="italic">{block.text}</span>
      </div>
    );

  if (block.type === "text")
    return (
      <div className="text-slate-100 text-sm leading-relaxed bg-panel2/40 rounded-xl px-4 py-3
        [&_strong]:font-semibold [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-2 [&_h3]:font-semibold
        [&_h3]:mt-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-0.5
        [&_p]:my-1.5 [&_code]:bg-ink [&_code]:px-1 [&_code]:rounded">
        <ReactMarkdown>{block.text ?? ""}</ReactMarkdown>
      </div>
    );

  if (block.type === "table") {
    const fmt = (v: any) =>
      typeof v === "number" ? new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(v)
        : v == null ? "—" : String(v);
    return (
      <div className="overflow-auto rounded-lg border border-edge">
        <table className="w-full text-sm">
          <thead><tr className="text-muted text-left bg-panel2/50 text-xs uppercase tracking-wide">
            {block.columns?.map((c) => <th key={c} className="py-2 px-3 font-medium">{c}</th>)}
          </tr></thead>
          <tbody>
            {block.rows?.map((r, ri) => (
              <tr key={ri} className="border-t border-edge">
                {(Array.isArray(r) ? r : block.columns?.map((c) => (r as any)[c]))?.map((cell: any, ci: number) => (
                  <td key={ci} className="py-2 px-3 text-slate-200 font-mono text-xs">{fmt(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (block.type === "chart") {
    if (block.vega) return <VegaChart spec={block.vega} />;
    return (
      <div className="rounded-lg border border-edge p-3 text-xs text-muted">
        Chart: {block.spec?.mark} of {block.spec?.y} by {block.spec?.x}
      </div>
    );
  }

  if (block.type === "sql")
    return (
      <details className="bg-ink border border-edge rounded-xl p-3">
        <summary className="cursor-pointer text-sm text-accent2">Show generated SQL</summary>
        <pre className="text-[11px] text-slate-300 mt-2 overflow-auto whitespace-pre-wrap">{block.sql}</pre>
      </details>
    );

  return null;
}

function VegaChart({ spec }: { spec: any }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    let view: any;
    const themed = {
      ...spec, width: "container", background: "transparent",
      config: {
        ...(spec.config || {}),
        axis: { labelColor: "#8aa0c0", titleColor: "#8aa0c0", gridColor: "rgba(138,160,192,0.15)", domainColor: "rgba(138,160,192,0.3)" },
        legend: { labelColor: "#8aa0c0", titleColor: "#8aa0c0" },
        title: { color: "#e2e8f0" },
        view: { stroke: "transparent" },
      },
    };
    vegaEmbed(ref.current, themed as any, { actions: false, renderer: "svg" })
      .then((res: any) => { view = res.view; }).catch(() => {});
    return () => { try { view?.finalize(); } catch { /* noop */ } };
  }, [spec]);
  return (
    <div className="rounded-lg border border-edge p-3">
      <div ref={ref} className="w-full overflow-x-auto" />
    </div>
  );
}
