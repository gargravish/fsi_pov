import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Card, SectionTitle, Badge, Loading } from "../components/ui";
import ForecastChart from "../components/ForecastChart";

const METRICS = [{ id: "nna", label: "Net New Money" }, { id: "aum", label: "AuM" }, { id: "revenue", label: "Revenue" }];
const DIVS = ["all", "GWM", "P&C", "Asset Management", "Investment Bank"];
const REGIONS = ["all", "Switzerland", "EMEA", "Americas", "APAC"];

export default function Forecast() {
  const [metric, setMetric] = useState("nna");
  const [division, setDivision] = useState("all");
  const [region, setRegion] = useState("all");
  const { data } = useQuery({
    queryKey: ["forecast", metric, division, region],
    queryFn: () => api.forecast(metric, division, region),
  });

  return (
    <div className="space-y-6">
      <SectionTitle kicker="AI.FORECAST · TimesFM 2.5" title="Forecast Room"
        sub="Zero-training, multi-series forecasting of AuM, Net New Money and revenue by division × region — planning toward the $200bn NNA/yr ambition." />

      <Card>
        <div className="flex flex-wrap gap-2 mb-4">
          {METRICS.map((m) => (
            <button key={m.id} onClick={() => setMetric(m.id)}
              className={metric === m.id ? "btn" : "btn-ghost"}>{m.label}</button>
          ))}
          <div className="flex-1" />
          <select className="input w-auto" value={division} onChange={(e) => setDivision(e.target.value)}>
            {DIVS.map((d) => <option key={d} value={d}>{d === "all" ? "All divisions" : d}</option>)}
          </select>
          <select className="input w-auto" value={region} onChange={(e) => setRegion(e.target.value)}>
            {REGIONS.map((r) => <option key={r} value={r}>{r === "all" ? "All regions" : r}</option>)}
          </select>
        </div>
        {!data ? <Loading /> : (
          <>
            <ForecastChart data={data} />
            <div className="mt-4 p-4 rounded-xl bg-panel2/50 border border-edge">
              <Badge tone="blue">AI commentary</Badge>
              <p className="text-sm text-slate-200 mt-2">{data.commentary}</p>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
