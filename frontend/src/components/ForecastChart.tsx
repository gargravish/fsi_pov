import {
  Area, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend,
} from "recharts";
import { ForecastResult } from "../lib/types";

export default function ForecastChart({ data }: { data: ForecastResult }) {
  const merged = [
    ...data.history.map((p) => ({ ts: p.ts, actual: p.actual ?? p.yhat })),
    ...data.forecast.map((p) => ({ ts: p.ts, forecast: p.yhat, lo: p.lo, hi: p.hi, band: [p.lo, p.hi] })),
  ];
  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={merged} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#1e2a45" vertical={false} />
        <XAxis dataKey="ts" tick={{ fill: "#8aa0c0", fontSize: 11 }} interval="preserveStartEnd" />
        <YAxis tick={{ fill: "#8aa0c0", fontSize: 11 }} width={50} />
        <Tooltip contentStyle={{ background: "#0f1729", border: "1px solid #1e2a45", borderRadius: 12 }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area type="monotone" dataKey="band" stroke="none" fill="#38bdf8" fillOpacity={0.12} name="90% interval" />
        <Line type="monotone" dataKey="actual" stroke="#e2e8f0" strokeWidth={2} dot={false} name="Actual" />
        <Line type="monotone" dataKey="forecast" stroke="#38bdf8" strokeWidth={2.5} dot={false} name="Forecast (TimesFM)" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
