import { useState } from "react";
import { api } from "../lib/api";
import { Card, SectionTitle, Badge, Loading } from "../components/ui";
import { DocHit } from "../lib/types";
import { Search, FileText } from "lucide-react";

export default function Research() {
  const [q, setQ] = useState("CIO view on private credit for UHNW clients");
  const [hits, setHits] = useState<DocHit[]>([]);
  const [answer, setAnswer] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    if (!q.trim()) return;
    setBusy(true); setAnswer(null);
    const [h, a] = await Promise.all([api.research(q), api.researchAnswer(q)]);
    setHits(h); setAnswer(a); setBusy(false);
  }

  return (
    <div className="space-y-6">
      <SectionTitle kicker="Autonomous embeddings · AI.SEARCH" title="Research Brain"
        sub="Grounded answers from CIO research, KYC and suitability documents — semantic search over autonomous embeddings, with citations back to the source document." />

      <Card>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-3 text-muted" />
            <input className="input pl-9" value={q} onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run()} placeholder="Search research & documents…" />
          </div>
          <button className="btn" disabled={busy} onClick={run}>Search</button>
        </div>
      </Card>

      {busy && <Loading label="Searching documents…" />}

      {answer && (
        <Card>
          <Badge tone="blue">Grounded answer (RAG)</Badge>
          <p className="text-slate-100 mt-2">{answer.answer}</p>
          <div className="flex gap-2 flex-wrap mt-3">
            {answer.citations.map((c: any) => (
              <span key={c.document_id} className="chip"><FileText size={12} /> {c.document_id}</span>
            ))}
          </div>
        </Card>
      )}

      {hits.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {hits.map((h) => (
            <Card key={h.document_id}>
              <div className="flex items-center justify-between">
                <Badge>{h.doc_type}</Badge>
                <span className="text-xs text-accent2">{Math.round(h.score * 100)}% match</span>
              </div>
              <div className="font-semibold text-white mt-2 text-sm">{h.title}</div>
              <p className="text-xs text-muted mt-1">{h.snippet}</p>
              <div className="text-[10px] text-muted/60 mt-2 truncate">{h.gcs_uri}</div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
