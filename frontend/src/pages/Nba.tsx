import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Card, SectionTitle, Badge, Loading, fmtUsd, SourceBadge } from "../components/ui";
import GraphCanvas from "../components/GraphCanvas";
import { Search, Mail, Copy, Check, Loader2 } from "lucide-react";

export default function Nba() {
  const [q, setQ] = useState("");
  const [cid, setCid] = useState<string | null>(null);
  const { data: hits } = useQuery({ queryKey: ["csearch", q], queryFn: () => api.clientSearch(q) });
  const { data: nba } = useQuery({ queryKey: ["nba", cid], queryFn: () => api.nba(cid!), enabled: !!cid });

  // per-action draft note state
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [drafting, setDrafting] = useState<number | null>(null);
  const [copied, setCopied] = useState<number | null>(null);

  async function draft(i: number, product: string) {
    if (!cid) return;
    setDrafting(i);
    try {
      const r = await api.nbaDraft(cid, product);
      setDrafts((d) => ({ ...d, [i]: r.note }));
    } finally {
      setDrafting(null);
    }
  }
  function copy(i: number) {
    navigator.clipboard?.writeText(drafts[i] ?? "");
    setCopied(i); setTimeout(() => setCopied(null), 1800);
  }

  // reset drafts when the client changes
  function selectClient(id: string) {
    setCid(id); setDrafts({}); setDrafting(null); setCopied(null);
  }

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
              <button key={h.client_id} onClick={() => selectClient(h.client_id)}
                className={`w-full text-left p-3 rounded-xl border transition ${cid === h.client_id ? "border-accent bg-panel2" : "border-edge hover:bg-panel2/60"}`}>
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm text-white truncate">{h.full_name}</div>
                  <SourceBadge source_banks={h.source_banks} dual_banked={h.dual_banked} />
                </div>
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
                    <button className="btn-ghost mt-3" disabled={drafting === i}
                      onClick={() => draft(i, a.product)}>
                      {drafting === i ? <Loader2 size={13} className="animate-spin" /> : <Mail size={13} />}
                      {drafts[i] ? "Regenerate advisor note" : "Draft advisor note"}
                    </button>

                    {drafts[i] && (
                      <div className="mt-3 rounded-xl border border-edge bg-ink overflow-hidden">
                        <div className="flex items-center justify-between px-3 py-2 border-b border-edge bg-panel2/40">
                          <span className="text-xs text-white flex items-center gap-2"><Mail size={12} className="text-accent2" /> Advisor note</span>
                          <button onClick={() => copy(i)} className="btn-ghost text-xs py-1">
                            {copied === i ? <Check size={12} /> : <Copy size={12} />} {copied === i ? "Copied" : "Copy"}
                          </button>
                        </div>
                        <pre className="text-sm text-slate-200 whitespace-pre-wrap font-sans leading-relaxed p-3">{drafts[i]}</pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {nba.cross_platform?.recommendations && nba.cross_platform.recommendations.length > 0 && (
                <div className="pt-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-white">Cross-platform opportunity</h3>
                    <Badge tone="amber">{nba.cross_platform.home_platform}-only client</Badge>
                  </div>
                  <p className="text-xs text-muted mt-1 mb-3">
                    {nba.client?.full_name ?? "This client"} banks only with {nba.cross_platform.home_platform}.
                    These <span className="text-accent2">{nba.cross_platform.other_platform}</span>-originated
                    capabilities are now on the unified shelf post-integration.
                  </p>
                  <div className="space-y-3">
                    {nba.cross_platform.recommendations.map((r, k) => {
                      const i = 100 + k; // offset to avoid clashing with action indices
                      return (
                        <div key={i} className="card p-4 border-amber-500/30 bg-amber-500/5">
                          <div className="flex items-center justify-between">
                            <div className="font-semibold text-white">{r.product}</div>
                            <Badge tone="amber">{r.origin_platform} → now available</Badge>
                          </div>
                          <p className="text-sm text-muted mt-2">{r.rationale}</p>
                          <button className="btn-ghost mt-3" disabled={drafting === i}
                            onClick={() => draft(i, r.product)}>
                            {drafting === i ? <Loader2 size={13} className="animate-spin" /> : <Mail size={13} />}
                            {drafts[i] ? "Regenerate advisor note" : "Draft advisor note"}
                          </button>
                          {drafts[i] && (
                            <div className="mt-3 rounded-xl border border-edge bg-ink overflow-hidden">
                              <div className="flex items-center justify-between px-3 py-2 border-b border-edge bg-panel2/40">
                                <span className="text-xs text-white flex items-center gap-2"><Mail size={12} className="text-accent2" /> Advisor note</span>
                                <button onClick={() => copy(i)} className="btn-ghost text-xs py-1">
                                  {copied === i ? <Check size={12} /> : <Copy size={12} />} {copied === i ? "Copied" : "Copy"}
                                </button>
                              </div>
                              <pre className="text-sm text-slate-200 whitespace-pre-wrap font-sans leading-relaxed p-3">{drafts[i]}</pre>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
