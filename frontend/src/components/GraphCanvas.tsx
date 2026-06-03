import { GraphData } from "../lib/types";

const COLORS: Record<string, string> = {
  client: "#e60028",
  household: "#38bdf8",
  account: "#22c55e",
  advisor: "#f59e0b",
};
const RISK: Record<string, string> = { low: "#22c55e", med: "#f59e0b", high: "#e60028" };

export default function GraphCanvas({ data, height = 360 }: { data: GraphData; height?: number }) {
  const w = 640;
  const cx = w / 2;
  const cy = height / 2;
  const nodes = data.nodes ?? [];
  const center = nodes[0];
  const others = nodes.slice(1);
  const pos: Record<string, { x: number; y: number }> = {};
  if (center) pos[center.id] = { x: cx, y: cy };
  others.forEach((n, i) => {
    const a = (2 * Math.PI * i) / Math.max(others.length, 1);
    pos[n.id] = { x: cx + Math.cos(a) * 220, y: cy + Math.sin(a) * (height / 2 - 50) };
  });

  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" style={{ height }}>
      {(data.edges ?? []).map((e, i) => {
        const s = pos[e.source];
        const t = pos[e.target];
        if (!s || !t) return null;
        return (
          <g key={i}>
            <line x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="#1e2a45" strokeWidth={1.5} />
            {(e.label || e.amount) && (
              <text x={(s.x + t.x) / 2} y={(s.y + t.y) / 2 - 4} fill="#8aa0c0" fontSize={9} textAnchor="middle">
                {e.label ?? `$${e.amount}`}
              </text>
            )}
          </g>
        );
      })}
      {nodes.map((n) => {
        const p = pos[n.id];
        if (!p) return null;
        const color = n.risk ? RISK[n.risk] : COLORS[n.type] ?? "#8aa0c0";
        const r = n.id === center?.id ? 26 : 18;
        return (
          <g key={n.id}>
            <circle cx={p.x} cy={p.y} r={r} fill={color} fillOpacity={0.18} stroke={color} strokeWidth={2} />
            <text x={p.x} y={p.y + r + 14} fill="#cbd5e1" fontSize={10} textAnchor="middle">
              {n.label.length > 22 ? n.label.slice(0, 21) + "…" : n.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
