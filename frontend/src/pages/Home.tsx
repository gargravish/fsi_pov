import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Card, Stat, Badge, Loading, fmtNum } from "../components/ui";
import {
  Combine, Network, ShieldAlert, TrendingUp, MessagesSquare, FileSearch,
  GitGraph, Boxes, Bot, ArrowRight,
} from "lucide-react";

const TILES = [
  { to: "/unify", icon: Combine, title: "Unify & Resolve", desc: "Two banks → one Client 360", cap: "AI.GENERATE_TABLE · embeddings · VECTOR_SEARCH" },
  { to: "/nba", icon: Network, title: "Next-Best-Action", desc: "Grow share-of-wallet", cap: "BigQuery Graph (GQL) · VECTOR_SEARCH" },
  { to: "/retention", icon: ShieldAlert, title: "Flight-Risk Sentinel", desc: "Protect the asset base", cap: "TabularFM" },
  { to: "/forecast", icon: TrendingUp, title: "Forecast Room", desc: "AuM / NNA / revenue", cap: "AI.FORECAST · TimesFM 2.5" },
  { to: "/ask", icon: MessagesSquare, title: "Ask Helix", desc: "Query the estate in English", cap: "Conversational Analytics" },
  { to: "/research", icon: FileSearch, title: "Research Brain", desc: "Grounded CIO / KYC answers", cap: "Autonomous embeddings · AI.SEARCH" },
  { to: "/network", icon: GitGraph, title: "Network Guard", desc: "AML / UBO networks", cap: "BigQuery Graph" },
  { to: "/segments", icon: Boxes, title: "Segment Studio", desc: "Behavioural micro-segments", cap: "BigFrames · KMeans" },
  { to: "/agents", icon: Bot, title: "Agent Console", desc: "DE ⇄ DS agents over A2A", cap: "ADK · A2A · BigQuery MCP" },
];

export default function Home() {
  const { data: k } = useQuery({ queryKey: ["kpis"], queryFn: api.kpis });

  return (
    <div className="space-y-7">
      <Card className="relative overflow-hidden">
        <div className="absolute -right-10 -top-10 h-48 w-48 rounded-full bg-accent/20 blur-3xl" />
        <Badge tone="red">BigQuery Agentic Data Platform · POV</Badge>
        <h1 className="text-3xl font-extrabold text-white mt-3 max-w-3xl leading-tight">
          From two banks and two of everything to one agentic intelligence layer.
        </h1>
        <p className="text-muted mt-2 max-w-3xl">
          FSI Helix unifies the Apex Bank + Summit Bank estate into one governed BigQuery Client 360,
          then runs autonomous embeddings, TimesFM forecasting, TabularFM risk, BigQuery Graph and
          collaborating agents — all <span className="text-slate-200">inside the warehouse</span>,
          no data movement, no separate ML platform.
        </p>
      </Card>

      {!k ? <Loading /> : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <Stat label="Clients unified" value={fmtNum(k.clients)} />
          <Stat label="Assets under mgmt" value={`$${(k.aum_usd_bn).toFixed(0)}bn`} sub="synthetic estate" />
          <Stat label="Dual-banked" value={`${k.dual_banked_pct}%`} sub="retention priority" />
          <Stat label="Cross-sell targets" value={fmtNum(k.cross_sell_opportunity ?? 0)} sub="single-bank clients" />
          <Stat label="NNA (2026)" value={`$${(k.nna_ytd_usd_m / 1000).toFixed(1)}bn`} sub="toward $200bn/yr" />
          <Stat label="Entity-res accuracy" value={`${k.er_accuracy}%`} />
        </div>
      )}

      <div>
        <h2 className="text-lg font-bold text-white mb-3">Business use cases</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {TILES.map((t) => (
            <Link key={t.to} to={t.to} className="card p-5 hover:border-accent2/60 transition group">
              <div className="flex items-start justify-between">
                <div className="h-10 w-10 rounded-xl bg-panel2 border border-edge grid place-items-center text-accent2">
                  <t.icon size={20} />
                </div>
                <ArrowRight size={16} className="text-muted group-hover:text-white transition" />
              </div>
              <div className="font-semibold text-white mt-3">{t.title}</div>
              <div className="text-sm text-muted">{t.desc}</div>
              <div className="text-[11px] text-accent2/80 mt-3 font-medium">{t.cap}</div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
