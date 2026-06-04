import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { api } from "../lib/api";
import { Card, SectionTitle, Badge, Loading, fmtUsd, SourceBadge } from "../components/ui";
import { Sparkles, Copy, Check, Mail, Target, Gift, Megaphone, ChevronRight } from "lucide-react";

function riskTone(r: number) {
  return r >= 0.7 ? "red" : r >= 0.45 ? "amber" : "green";
}

export default function Retention() {
  const { data: pipeline } = useQuery({ queryKey: ["pipeline"], queryFn: api.retentionPipeline });
  const { data: scores } = useQuery({ queryKey: ["scores"], queryFn: api.retentionScores });
  const [sel, setSel] = useState<string | null>(null);

  const { data: campaign, isFetching } = useQuery({
    queryKey: ["campaign", sel],
    queryFn: () => api.retentionCampaign(sel!),
    enabled: !!sel,
  });

  return (
    <div className="space-y-6">
      <SectionTitle kicker="TabularFM + BigQuery Graph + Gemini" title="Flight-Risk Sentinel"
        sub="A zero-tuning TabularFM classifier predicts attrition 60–90 days out. Select a client to generate a targeted retention campaign — Gemini grounds it in the client's 360 (household whitespace via GQL, asset mix, recent flows) and drafts a ready-to-send advisor email." />

      <Card>
        <h3 className="font-semibold text-white mb-3">Outflow review pipeline — next 12 weeks</h3>
        {!pipeline ? <Loading /> : (
          <ResponsiveContainer width="100%" height={180}>
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

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <Card className="lg:col-span-2">
          <h3 className="font-semibold text-white mb-1">Highest flight-risk clients</h3>
          {scores && scores.length > 0 && (() => {
            const dual = scores.filter((s) => s.dual_banked).length;
            const pct = Math.round((dual / scores.length) * 100);
            return (
              <p className="text-xs text-muted mb-3">
                <span className="text-accent2 font-semibold">{pct}%</span> of the top {scores.length} are{" "}
                <span className="text-white">dual-banked (UBS + Credit Suisse)</span> — the integration is the
                #1 flight-risk driver. Single-bank clients are lower risk but a growth opportunity (see Next-Best-Action).
              </p>
            );
          })()}
          {!scores ? <Loading /> : (
            <div className="space-y-2">
              {scores.map((s) => (
                <button key={s.client_id} onClick={() => setSel(s.client_id)}
                  className={`w-full text-left p-3 rounded-xl border transition ${
                    sel === s.client_id ? "bg-panel2 border-accent2" : "bg-panel2/50 border-edge hover:border-accent2/50"}`}>
                  <div className="flex items-center justify-between">
                    <div className="min-w-0">
                      <span className="text-white font-medium">{s.full_name}</span>
                      <span className="text-muted text-xs ml-2">{s.segment_tier}</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <SourceBadge source_banks={s.source_banks} dual_banked={s.dual_banked} />
                      <Badge tone={riskTone(s.flight_risk)}>{Math.round(s.flight_risk * 100)}%</Badge>
                      <ChevronRight size={14} className={sel === s.client_id ? "text-accent2" : "text-muted"} />
                    </div>
                  </div>
                  <div className="flex gap-1.5 flex-wrap mt-2">
                    {s.drivers.map((d, i) => <span key={i} className="chip">{d}</span>)}
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>

        <Card className="lg:col-span-3">
          {!sel ? (
            <div className="h-full grid place-items-center text-center text-muted text-sm py-16">
              <div>
                <Megaphone size={28} className="mx-auto mb-3 text-accent2" />
                Select a client to generate a targeted retention campaign.
              </div>
            </div>
          ) : isFetching || !campaign ? (
            <Loading label="Building the campaign — GQL household 360 + Gemini draft…" />
          ) : (
            <CampaignView c={campaign} />
          )}
        </Card>
      </div>
    </div>
  );
}

function CampaignView({ c }: { c: any }) {
  const [copied, setCopied] = useState(false);
  const ctx = c.context ?? {};
  const camp = c.campaign ?? {};
  const copy = () => {
    navigator.clipboard?.writeText(`Subject: ${camp.email_subject}\n\n${camp.email_body}`);
    setCopied(true); setTimeout(() => setCopied(false), 1800);
  };
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-white font-semibold flex items-center gap-2">
            {c.client.full_name}
            {c.client.dual_banked && <Badge tone="red">dual-banked</Badge>}
          </div>
          <div className="text-xs text-muted">{c.client.segment_tier} · {c.client.booking_centre} · {fmtUsd(c.client.total_aum_usd)} AuM · advisor {ctx.advisor?.name}</div>
        </div>
        <Badge tone="red">{Math.round((c.flight_risk ?? 0) * 100)}% flight risk</Badge>
      </div>

      {/* 360 context */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <div className="p-2.5 rounded-lg bg-panel2/50 border border-edge">
          <div className="text-[11px] text-muted mb-1">Asset mix</div>
          {ctx.asset_mix?.slice(0, 4).map((a: any) => (
            <div key={a.asset_class} className="flex justify-between text-xs"><span className="text-slate-300">{a.asset_class}</span><span className="text-white">{a.pct}%</span></div>
          ))}
        </div>
        <div className="p-2.5 rounded-lg bg-panel2/50 border border-edge">
          <div className="text-[11px] text-muted mb-1">Household whitespace (GQL)</div>
          {ctx.household_whitespace?.length ? ctx.household_whitespace.map((w: any, i: number) => (
            <div key={i} className="flex justify-between text-xs"><span className="text-slate-300">{w.product}</span><span className="text-accent2">×{w.household_signal}</span></div>
          )) : <div className="text-xs text-muted">none</div>}
        </div>
        <div className="p-2.5 rounded-lg bg-panel2/50 border border-edge">
          <div className="text-[11px] text-muted mb-1">Net flow (6m)</div>
          <div className={`text-lg font-bold ${(ctx.recent_net_flow_usd ?? 0) < 0 ? "text-red-300" : "text-emerald-300"}`}>
            {fmtUsd(ctx.recent_net_flow_usd ?? 0)}
          </div>
        </div>
      </div>

      {/* campaign */}
      <div className="space-y-2.5">
        <Field icon={Target} label="Objective" text={camp.objective} />
        <Field icon={Gift} label="Retention offer" text={camp.retention_offer} />
        <Field icon={Sparkles} label="Next-best-action" text={camp.next_best_action} accent />
        <Field icon={Megaphone} label="Channel" text={camp.preferred_channel} />
      </div>

      {camp.talking_points?.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5">Talking points</div>
          <ul className="list-disc pl-5 space-y-1 text-sm text-slate-200">
            {camp.talking_points.map((t: string, i: number) => <li key={i}>{t}</li>)}
          </ul>
        </div>
      )}

      {/* email draft */}
      <div className="rounded-xl border border-edge bg-ink overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 border-b border-edge bg-panel2/40">
          <span className="text-sm text-white flex items-center gap-2"><Mail size={14} className="text-accent2" /> Draft outreach email</span>
          <button onClick={copy} className="btn-ghost text-xs py-1">
            {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? "Copied" : "Copy"}
          </button>
        </div>
        <div className="p-3">
          <div className="text-sm text-white font-medium mb-2">{camp.email_subject}</div>
          <pre className="text-sm text-slate-200 whitespace-pre-wrap font-sans leading-relaxed">{camp.email_body}</pre>
        </div>
      </div>
    </div>
  );
}

function Field({ icon: Icon, label, text, accent }: { icon: any; label: string; text?: string; accent?: boolean }) {
  return (
    <div className={`flex gap-2.5 p-2.5 rounded-lg border ${accent ? "bg-accent2/10 border-accent2/40" : "bg-panel2/40 border-edge"}`}>
      <Icon size={15} className={accent ? "text-accent2 mt-0.5 shrink-0" : "text-muted mt-0.5 shrink-0"} />
      <div>
        <div className="text-[11px] text-muted uppercase tracking-wide">{label}</div>
        <div className="text-sm text-slate-100">{text}</div>
      </div>
    </div>
  );
}
