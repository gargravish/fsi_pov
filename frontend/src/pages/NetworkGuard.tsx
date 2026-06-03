import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Card, SectionTitle, Badge, Loading } from "../components/ui";
import GraphCanvas from "../components/GraphCanvas";
import { ChevronRight } from "lucide-react";

const sevTone = (s: string) => (s === "high" ? "red" : s === "medium" ? "amber" : "green");

export default function NetworkGuard() {
  const { data } = useQuery({ queryKey: ["network"], queryFn: api.network });
  const [sel, setSel] = useState(0);

  const anomalies = data?.anomalies ?? [];
  const active = anomalies[sel];

  return (
    <div className="space-y-6">
      <SectionTitle kicker="BigQuery Graph" title="Network Guard"
        sub="Financial-crime defence over the client / entity / transaction graph. Multi-hop GQL surfaces structuring, ultimate-beneficial-owner risk and cross-bank concentration. Click a pattern to inspect the actual entities and transactions behind it." />

      {!data ? <Loading /> : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* left: clickable pattern list */}
          <Card className="lg:col-span-2">
            <h3 className="font-semibold text-white mb-3">Suspicious patterns</h3>
            <div className="space-y-2">
              {anomalies.map((a: any, i: number) => (
                <button key={a.id ?? i} onClick={() => setSel(i)}
                  className={`w-full text-left p-3 rounded-xl border transition ${
                    i === sel ? "bg-panel2 border-accent2" : "bg-panel2/40 border-edge hover:border-accent2/50"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-white text-sm">{a.type}</span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <Badge tone={sevTone(a.severity)}>{a.severity}</Badge>
                      <ChevronRight size={14} className={i === sel ? "text-accent2" : "text-muted"} />
                    </div>
                  </div>
                  <p className="text-xs text-muted mt-1">{a.summary}</p>
                </button>
              ))}
              {anomalies.length === 0 && <div className="text-muted text-sm py-6 text-center">No patterns detected.</div>}
            </div>
          </Card>

          {/* right: selected pattern detail */}
          <Card className="lg:col-span-3">
            {!active ? <Loading /> : (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-white">{active.type}</h3>
                  <Badge tone={sevTone(active.severity)}>{active.severity}</Badge>
                </div>
                <p className="text-sm text-muted">{active.summary}</p>

                <div className="rounded-xl bg-ink border border-edge">
                  <GraphCanvas data={active.subgraph} height={340} />
                </div>
                <p className="text-[11px] text-muted">
                  Node colour = risk tier · edge label = transfer amount (USD) / relationship.
                </p>

                {active.details?.rows?.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5">
                      Underlying records ({active.details.rows.length})
                    </div>
                    <div className="overflow-auto rounded-lg border border-edge max-h-52">
                      <table className="w-full text-xs">
                        <thead><tr className="text-muted bg-panel2/50 text-left sticky top-0">
                          {active.details.columns.map((c: string) => <th key={c} className="py-1.5 px-2 font-medium">{c}</th>)}
                        </tr></thead>
                        <tbody>
                          {active.details.rows.map((r: any[], ri: number) => (
                            <tr key={ri} className="border-t border-edge">
                              {r.map((cell, ci) => <td key={ci} className="py-1.5 px-2 text-slate-200 font-mono">{String(cell)}</td>)}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {active.gql && (
                  <details className="bg-ink border border-edge rounded-lg p-3">
                    <summary className="cursor-pointer text-sm text-accent2">Show GQL (multi-hop graph query)</summary>
                    <pre className="text-[11px] text-slate-300 mt-2 overflow-auto whitespace-pre-wrap">{active.gql}</pre>
                  </details>
                )}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
