import { useQuery } from "@tanstack/react-query";
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis, ResponsiveContainer, Tooltip, CartesianGrid,
} from "recharts";
import { api } from "../lib/api";
import { Card, SectionTitle, Badge, Loading, fmtUsd, fmtNum } from "../components/ui";

export default function Segments() {
  const { data } = useQuery({ queryKey: ["segments"], queryFn: api.segments });

  const scatter = (data ?? []).map((s, i) => ({
    x: i, y: s.avg_aum_usd, z: s.size, label: s.label, attr: s.attrition_index,
  }));

  return (
    <div className="space-y-6">
      <SectionTitle kicker="BigFrames · KMeans · AI naming" title="Segment Studio"
        sub="Behavioural micro-segments built with BigFrames KMeans over the client feature frame, then named by Gemini — move beyond static wealth-tier buckets." />

      {!data ? <Loading /> : (
        <>
          <Card>
            <h3 className="font-semibold text-white mb-3">Segment map (size = bubble, AuM = height)</h3>
            <ResponsiveContainer width="100%" height={280}>
              <ScatterChart margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
                <CartesianGrid stroke="#1e2a45" />
                <XAxis type="number" dataKey="x" tick={false} axisLine={false} />
                <YAxis type="number" dataKey="y" tick={{ fill: "#8aa0c0", fontSize: 10 }}
                  tickFormatter={(v) => fmtUsd(v)} width={60} />
                <ZAxis type="number" dataKey="z" range={[80, 800]} />
                <Tooltip contentStyle={{ background: "#0f1729", border: "1px solid #1e2a45", borderRadius: 12 }}
                  formatter={(_v, _n, p: any) => [p.payload.label, ""]} />
                <Scatter data={scatter} fill="#e60028" fillOpacity={0.55} />
              </ScatterChart>
            </ResponsiveContainer>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {data.map((s) => (
              <Card key={s.id}>
                <div className="font-semibold text-white text-sm leading-snug">{s.label}</div>
                <div className="mt-2 space-y-1 text-xs text-muted">
                  <div>Size: <span className="text-slate-200">{fmtNum(s.size)}</span></div>
                  <div>Avg AuM: <span className="text-slate-200">{fmtUsd(s.avg_aum_usd)}</span></div>
                  <div>Dominant: <span className="text-slate-200">{s.dominant_asset}</span></div>
                  {s.dual_banked_pct != null && (
                    <div>Dual-banked: <span className="text-slate-200">{s.dual_banked_pct}%</span> <span className="text-muted">(integration overlap)</span></div>
                  )}
                </div>
                <div className="mt-2 flex gap-1.5 flex-wrap">
                  <Badge tone={s.attrition_index > 0.25 ? "red" : s.attrition_index > 0.15 ? "amber" : "green"}>
                    attrition {Math.round(s.attrition_index * 100)}
                  </Badge>
                  {(s.dual_banked_pct ?? 0) >= 30 && <Badge tone="red">integration-sensitive</Badge>}
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
