import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { api } from "../lib/api";
import { Card, SectionTitle, Badge, Loading } from "../components/ui";

function riskTone(r: number) {
  return r >= 0.7 ? "red" : r >= 0.45 ? "amber" : "green";
}

export default function Retention() {
  const { data: pipeline } = useQuery({ queryKey: ["pipeline"], queryFn: api.retentionPipeline });
  const { data: scores } = useQuery({ queryKey: ["scores"], queryFn: api.retentionScores });

  return (
    <div className="space-y-6">
      <SectionTitle kicker="TabularFM" title="Flight-Risk Sentinel"
        sub="The integration is the moment of maximum flight risk. A zero-tuning TabularFM classifier predicts client attrition and NNA outflow 60–90 days out; Gemini drafts the save play." />

      <Card>
        <h3 className="font-semibold text-white mb-3">Outflow review pipeline — next 12 weeks</h3>
        {!pipeline ? <Loading /> : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={pipeline}>
              <CartesianGrid stroke="#1e2a45" vertical={false} />
              <XAxis dataKey="week" tick={{ fill: "#8aa0c0", fontSize: 10 }} />
              <YAxis tick={{ fill: "#8aa0c0", fontSize: 11 }} width={36} />
              <Tooltip contentStyle={{ background: "#0f1729", border: "1px solid #1e2a45", borderRadius: 12 }} />
              <Bar dataKey="count" fill="#1e2a45" radius={[4, 4, 0, 0]} />
              <Bar dataKey="high_risk" fill="#e60028" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Card>
        <h3 className="font-semibold text-white mb-3">Highest flight-risk clients</h3>
        {!scores ? <Loading /> : (
          <div className="space-y-2">
            {scores.map((s) => (
              <div key={s.client_id} className="p-3 rounded-xl bg-panel2/50 border border-edge">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-white font-medium">{s.full_name}</span>
                    <span className="text-muted text-xs ml-2">{s.segment_tier} · {s.client_id}</span>
                  </div>
                  <Badge tone={riskTone(s.flight_risk)}>{Math.round(s.flight_risk * 100)}% risk</Badge>
                </div>
                <div className="flex gap-2 flex-wrap mt-2">
                  {s.drivers.map((d, i) => <span key={i} className="chip">{d}</span>)}
                </div>
                <p className="text-sm text-muted mt-2"><span className="text-accent2">Save play:</span> {s.play}</p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
