import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Card, SectionTitle, Badge, Loading, fmtUsd } from "../components/ui";
import GraphCanvas from "../components/GraphCanvas";
import { Search } from "lucide-react";

export default function Nba() {
  const [q, setQ] = useState("");
  const [cid, setCid] = useState<string | null>(null);
  const { data: hits } = useQuery({ queryKey: ["csearch", q], queryFn: () => api.clientSearch(q) });
  const { data: nba } = useQuery({ queryKey: ["nba", cid], queryFn: () => api.nba(cid!), enabled: !!cid });

  return (
    <div className="space-y-6">
      <SectionTitle kicker="BigQuery Graph + Vector Search" title="Next-Best-Action"
        sub="Grow share-of-wallet across the household and family-office network. GQL traversal finds what household-mates hold; VECTOR_SEARCH finds behavioural look-alikes; Gemini drafts the advisor rationale." />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <div className="relative mb-3">
            <Search size={15} className="absolute left-3 top-3 text-muted" />
            <input className="input pl-9" placeholder="Search clients…" value={q}
              onChange={(e) => setQ(e.target.value)} />
          </div>
          <div className="space-y-1 max-h-[460px] overflow-auto">
            {(hits ?? []).map((h) => (
              <button key={h.client_id} onClick={() => setCid(h.client_id)}
                className={`w-full text-left p-3 rounded-xl border transition ${cid === h.client_id ? "border-accent bg-panel2" : "border-edge hover:bg-panel2/60"}`}>
                <div className="text-sm text-white">{h.full_name}</div>
                <div className="text-xs text-muted flex gap-2">
                  <span>{h.segment_tier}</span>·<span>{h.booking_centre}</span>·<span>{fmtUsd(h.total_aum_usd)}</span>
                </div>
              </button>
            ))}
          </div>
        </Card>

        <Card className="lg:col-span-2">
          {!cid ? (
            <div className="text-muted text-sm py-20 text-center">Select a client to see their household graph and next-best-actions.</div>
          ) : !nba ? <Loading /> : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-white">{nba.client?.full_name ?? cid} · household graph</h3>
                <Badge tone="blue">GQL MATCH</Badge>
              </div>
              <div className="rounded-xl bg-ink border border-edge">
                <GraphCanvas data={nba.graph} />
              </div>
              <h3 className="font-semibold text-white pt-2">Ranked next-best-actions</h3>
              <div className="space-y-3">
                {nba.actions.map((a, i) => (
                  <div key={i} className="card p-4">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-white">{a.product}</div>
                      <Badge tone="red">{Math.round(a.score * 100)}% fit</Badge>
                    </div>
                    <div className="flex gap-2 flex-wrap mt-2">
                      {a.signals.map((s, j) => <span key={j} className="chip">{s}</span>)}
                    </div>
                    <p className="text-sm text-muted mt-2">{a.rationale}</p>
                    <button className="btn-ghost mt-3">Draft advisor note</button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
