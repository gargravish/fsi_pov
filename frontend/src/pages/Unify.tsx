import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Card, SectionTitle, Badge, Loading, fmtNum } from "../components/ui";
import { Play, FileJson, FileSpreadsheet, FileText, FileCode, Database } from "lucide-react";

const ICON: Record<string, any> = {
  CSV: FileText, JSON: FileJson, NDJSON: FileJson, XML: FileCode,
  PARQUET: Database, XLSX: FileSpreadsheet, FIXED_WIDTH: FileText,
};

export default function Unify() {
  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: api.sources });
  const { data: result, refetch, isFetching } = useQuery({
    queryKey: ["unify"], queryFn: api.unify, enabled: false,
  });
  const [ran, setRan] = useState(false);

  return (
    <div className="space-y-6">
      <SectionTitle kicker="Data Engineering Agent" title="Unify & Resolve"
        sub="Collapse the fragmented Apex Bank + Summit Bank estate into one governed Client 360 — AI-mapped schemas and embedding-based entity resolution rediscover dual-banked clients." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">Fragmented sources</h3>
            <button className="btn" disabled={isFetching} onClick={() => { setRan(true); refetch(); }}>
              <Play size={15} /> {isFetching ? "Running…" : "Run unification"}
            </button>
          </div>
          {!sources ? <Loading /> : (
            <div className="space-y-2">
              {sources.map((s, i) => {
                const Ic = ICON[s.format] ?? FileText;
                return (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-panel2/60 border border-edge">
                    <Ic size={18} className="text-accent2" />
                    <div className="flex-1">
                      <div className="text-sm text-white">{s.bank} · {s.entity}</div>
                      <div className="text-xs text-muted">{fmtNum(s.rows)} rows</div>
                    </div>
                    <span className="chip">{s.format}</span>
                    <Badge tone={ran ? "green" : "default"}>{ran ? "mapped" : s.status}</Badge>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card>
          <h3 className="font-semibold text-white mb-4">Resolution result</h3>
          {!result ? (
            <div className="text-muted text-sm py-10 text-center">
              Click <span className="text-white">Run unification</span> to map schemas and resolve
              dual-banked clients.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="card p-3"><div className="text-xs text-muted">Fields mapped</div><div className="text-xl font-bold text-white">{result.mapped_fields}</div></div>
                <div className="card p-3"><div className="text-xs text-muted">Dual-banked</div><div className="text-xl font-bold text-white">{fmtNum(result.dual_banked_clusters)}</div></div>
                <div className="card p-3"><div className="text-xs text-muted">ER accuracy</div><div className="text-xl font-bold text-accent2">{result.accuracy}%</div></div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <div className="text-xs text-muted mb-1">Before — raw Summit Bank JSON</div>
                  <pre className="text-[11px] bg-ink border border-edge rounded-xl p-3 overflow-auto max-h-56 text-amber-200">{JSON.stringify(result.before, null, 2)}</pre>
                </div>
                <div>
                  <div className="text-xs text-muted mb-1">After — canonical Client 360</div>
                  <pre className="text-[11px] bg-ink border border-edge rounded-xl p-3 overflow-auto max-h-56 text-emerald-200">{JSON.stringify(result.after, null, 2)}</pre>
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
