import type {
  Kpis, Source, UnifyResult, ClientHit, NbaResult, RetentionScore,
  ForecastResult, KeyDriversResult, KeyDriver, DriverDrilldown, DocHit, Segment, AgentStep, AskBlock,
} from "./types";

// ---- AI.KEY_DRIVERS mock data + builders (module scope so both the ranked
// list and the per-driver drill-down draw from one consistent source) ---------
type KdSeg = [string, string][];
function kdMake(seg: KdSeg, interest: number, reference: number,
                unexpected: number, contribution: number, support: number): KeyDriver {
  const difference = +(interest - reference).toFixed(2);
  return {
    label: seg.map(([, v]) => v).join(" · "),
    segment: seg.map(([name, value]) => ({ name, value })),
    metric_interest_usd_m: interest, metric_reference_usd_m: reference,
    difference_usd_m: difference,
    relative_difference: reference ? +((interest - reference) / Math.abs(reference)).toFixed(4) : 0,
    unexpected_difference_usd_m: unexpected, contribution, apriori_support: support,
    direction: difference >= 0 ? "up" : "down",
  };
}
const KD_TABLES: Record<string, { label: string; direction: "higher" | "lower"; rows: KeyDriver[] }> = {
  nna: { label: "Net New Money", direction: "higher", rows: [
    kdMake([["region", "APAC"], ["segment_tier", "UHNW"]], 812, 540, 198, 0.214, 0.121),
    kdMake([["booking_centre", "Geneva"], ["banking", "Dual-banked (Apex + Summit)"]], 96, 318, -171, 0.165, 0.094),
    kdMake([["booking_centre", "Hong Kong"]], 604, 470, 121, 0.142, 0.158),
    kdMake([["segment_tier", "Family Office"], ["region", "EMEA"]], 288, 196, 88, 0.118, 0.067),
    kdMake([["booking_centre", "Zurich"], ["banking", "Dual-banked (Apex + Summit)"]], 142, 286, -109, 0.108, 0.102),
    kdMake([["segment_tier", "Affluent"], ["risk_profile", "Conservative"]], 174, 252, -64, 0.082, 0.144),
    kdMake([["region", "Americas"], ["segment_tier", "HNW"]], 356, 300, 47, 0.071, 0.116),
    kdMake([["risk_profile", "Aggressive"], ["region", "APAC"]], 228, 168, 54, 0.069, 0.058),
    kdMake([["segment_tier", "Institutional"]], 410, 372, 31, 0.044, 0.071),
  ] },
  inflow: { label: "Gross Inflows", direction: "higher", rows: [
    kdMake([["region", "APAC"], ["segment_tier", "UHNW"]], 1240, 980, 176, 0.198, 0.121),
    kdMake([["booking_centre", "Hong Kong"]], 1010, 860, 118, 0.151, 0.158),
    kdMake([["segment_tier", "Family Office"], ["region", "EMEA"]], 520, 410, 84, 0.122, 0.067),
    kdMake([["region", "Americas"], ["segment_tier", "HNW"]], 690, 600, 58, 0.094, 0.116),
    kdMake([["booking_centre", "Singapore"]], 470, 408, 46, 0.077, 0.083),
    kdMake([["segment_tier", "Affluent"], ["risk_profile", "Growth"]], 380, 352, 24, 0.051, 0.139),
  ] },
  outflow: { label: "Gross Outflows", direction: "lower", rows: [
    kdMake([["booking_centre", "Geneva"], ["banking", "Dual-banked (Apex + Summit)"]], 402, 214, 158, 0.231, 0.094),
    kdMake([["booking_centre", "Zurich"], ["banking", "Dual-banked (Apex + Summit)"]], 318, 198, 101, 0.164, 0.102),
    kdMake([["segment_tier", "Affluent"], ["risk_profile", "Conservative"]], 246, 188, 49, 0.097, 0.144),
    kdMake([["region", "EMEA"], ["segment_tier", "HNW"]], 290, 244, 38, 0.082, 0.131),
    kdMake([["booking_centre", "London"]], 210, 180, 27, 0.061, 0.088),
  ] },
};
const KD_COMMENTARY: Record<string, string> = {
  nna: "Net New Money rose overall, but the gain is uneven: **APAC UHNW** and **Hong Kong** pulled NNA well above the bankwide trend (+USD 198m / +USD 121m unexpected), while **dual-banked clients in Geneva and Zurich** dragged it down by far more than the trend explains (−USD 171m / −USD 109m unexpected) — the integration-overlap cohort to defend first. Sustaining APAC momentum while stemming Swiss dual-banked outflows is the clearest path to the $200bn net-new-money ambition.",
  inflow: "Gross inflows are driven by **APAC UHNW** and **Hong Kong**, which together contribute the bulk of the recent uplift and over-shoot the population trend — consistent with the post-integration push into Asia-Pacific wealth.",
  outflow: "The recent rise in outflows is concentrated in **dual-banked (Apex + Summit) clients booked in Geneva and Zurich** — the integration-overlap cohort — which exceed the bankwide outflow trend by the widest margin and warrant immediate retention attention.",
};
function kdResult(metric: string): KeyDriversResult {
  const t = KD_TABLES[metric] ?? KD_TABLES.nna;
  const rows = [...t.rows].sort((a, b) => Math.abs(b.unexpected_difference_usd_m) - Math.abs(a.unexpected_difference_usd_m));
  const ti = +rows.reduce((s, d) => s + d.metric_interest_usd_m, 0).toFixed(1);
  const tr = +rows.reduce((s, d) => s + d.metric_reference_usd_m, 0).toFixed(1);
  return {
    metric, metric_label: t.label, direction: t.direction,
    interest_period: "Most recent 6 months", reference_period: "Prior 6 months",
    total_interest_usd_m: ti, total_reference_usd_m: tr, net_change_usd_m: +(ti - tr).toFixed(1),
    drivers: rows, commentary: KD_COMMENTARY[metric] ?? KD_COMMENTARY.nna,
  };
}

const KD_HIST_MONTHS = ["2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
                        "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"];
const KD_FC_MONTHS = ["2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"];

const KD_DS = "raves-altostrat.FSI_POV";
const KD_COL: Record<string, [string, string]> = {
  nna: ["net_new_money_usd", "Net New Money"], inflow: ["inflow_usd", "Gross Inflows"], outflow: ["outflow_usd", "Gross Outflows"],
};
const KD_ALL_DIMS = ["segment_tier", "region", "booking_centre", "risk_profile", "banking"];
const kdDimExpr = (n: string) => n === "banking" ? "IF(c.dual_banked, 'Dual-banked (Apex + Summit)', 'Single-bank')" : `c.${n}`;
function kdWhere(pairs: { name: string; value: string }[]): string {
  const parts = pairs.map((p) => p.name === "banking"
    ? `c.dual_banked = ${p.value.toLowerCase().startsWith("dual") ? "TRUE" : "FALSE"}`
    : `${kdDimExpr(p.name)} = '${p.value}'`);
  return parts.join("\n     AND ") || "TRUE";
}
/** The real AI-function SQL behind each deep-dive stage, scoped to this segment. */
function kdSqlBlock(metric: string, pairs: { name: string; value: string }[],
                    recent: number, prior: number, good: boolean) {
  const [col, label] = KD_COL[metric] ?? KD_COL.nna;
  const where = kdWhere(pairs);
  const subs = KD_ALL_DIMS.filter((d) => !pairs.some((p) => p.name === d));
  const subSelect = subs.map((d) => `${kdDimExpr(d)} AS ${d}`).join(",\n            ");
  const subList = `[${subs.map((d) => `'${d}'`).join(", ")}]`;
  const segText = pairs.map((p) => p.value).join(" · ");
  return {
    anomalies:
`-- WHAT HAPPENED · AI.DETECT_ANOMALIES — flag the anomalous months in this
-- segment's monthly ${label} series (recent dip/spike vs its own history).
SELECT month, metric AS ${col}, is_anomaly, anomaly_probability
FROM AI.DETECT_ANOMALIES(
  (SELECT TIMESTAMP_TRUNC(TIMESTAMP(f.month), MONTH) AS month,
          SUM(f.${col}) AS metric
   FROM \`${KD_DS}.client_flows\` f
   JOIN \`${KD_DS}.clients\`  c USING (client_id)
   WHERE ${where}
     AND f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 12 MONTH)
   GROUP BY month),
  data_col              => 'metric',
  timestamp_col         => 'month',
  anomaly_prob_threshold => 0.95)
ORDER BY month;`,
    drivers:
`-- WHY IT HAPPENED · AI.KEY_DRIVERS — within this segment, rank the sub-segments
-- driving the change (recent 6m = interest vs prior 6m = reference).
SELECT * FROM AI.KEY_DRIVERS(
  (SELECT ${subSelect || "c.segment_tier"},
          f.${col} AS metric,
          f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 6 MONTH) AS is_recent
   FROM \`${KD_DS}.client_flows\` f
   JOIN \`${KD_DS}.clients\`  c USING (client_id)
   WHERE ${where}
     AND f.month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 12 MONTH)),
  metric_col         => 'metric',
  dimension_cols     => ${subList || "['segment_tier']"},
  interest_label_col => 'is_recent',
  top_k              => 10)
ORDER BY ABS(unexpected_difference) DESC;`,
    forecast:
`-- WHAT'S NEXT · AI.FORECAST (TimesFM 2.5) — 6-month forward path of this
-- segment's monthly ${label}, with a 90% prediction interval.
SELECT forecast_timestamp, forecast_value,
       prediction_interval_lower_bound, prediction_interval_upper_bound
FROM AI.FORECAST(
  (SELECT TIMESTAMP(f.month) AS month, SUM(f.${col}) AS v
   FROM \`${KD_DS}.client_flows\` f
   JOIN \`${KD_DS}.clients\`  c USING (client_id)
   WHERE ${where}
   GROUP BY month),
  data_col         => 'v',
  timestamp_col    => 'month',
  model            => 'TimesFM 2.5',
  horizon          => 6,
  confidence_level => 0.9)
ORDER BY forecast_timestamp;`,
    prevention:
`-- HOW TO ${good ? "SUSTAIN" : "PREVENT"} IT · AI.GENERATE — compliant actions grounded in the numbers.
SELECT AI.GENERATE(
  CONCAT('Recommend 3-4 concrete, compliant actions for a Apex Bank market head to ',
         '${good ? "sustain" : "prevent and reverse"} the recent ${label} move for the ',
         '"${segText}" segment. Recent 6m USD ${recent}m vs prior 6m USD ${prior}m. ',
         'Tie to the Apex-Summit integration and the \$200bn net-new-money ambition.'),
  connection_id => 'us-central1.vertex_conn',
  endpoint      => 'gemini-2.5-flash').result AS recommended_actions;`,
  };
}

function kdDrilldown(metric: string, label: string): DriverDrilldown {
  const t = KD_TABLES[metric] ?? KD_TABLES.nna;
  const d = t.rows.find((r) => r.label === label) ?? t.rows[0];
  const segLower = d.label.toLowerCase();
  const isDual = segLower.includes("dual-banked");
  const isApac = segLower.includes("apac") || segLower.includes("hong kong") || segLower.includes("singapore");
  const down = d.direction === "down";

  // 12-month trend: prior-6 around prior/6, recent-6 around recent/6 (visible step)
  const priorAvg = d.metric_reference_usd_m / 6;
  const recentAvg = d.metric_interest_usd_m / 6;
  const wig = (i: number) => 1 + (((i * 37) % 7) - 3) / 100; // ±3% deterministic
  const trend = KD_HIST_MONTHS.map((ts, i) => {
    const value = +((i < 6 ? priorAvg : recentAvg) * wig(i)).toFixed(2);
    // AI.DETECT_ANOMALIES would flag recent months that broke from prior history
    const is_anomaly = i >= 6 && (down ? value < priorAvg * 0.85 : value > priorAvg * 1.15);
    return { ts, value, is_anomaly };
  });

  // forecast: continue the recent run-rate; if it's a bad move (down NNA / up
  // outflow) the unmanaged trajectory keeps deteriorating, bands widen.
  const slope = (recentAvg - priorAvg) / 6;
  const forecast = KD_FC_MONTHS.map((ts, i) => {
    const yhat = +(recentAvg + slope * (i + 1) * 0.6).toFixed(2);
    const spread = Math.abs(yhat) * (0.07 + i * 0.015);
    return { ts, yhat, lo: +(yhat - spread).toFixed(2), hi: +(yhat + spread).toFixed(2) };
  });

  // RCA factors — sum roughly to the difference, tailored to the segment
  const diff = d.difference_usd_m;
  const factors: { factor: string; impact_usd_m: number; detail: string }[] = isDual
    ? [
        { factor: "Integration-overlap attrition", impact_usd_m: +(diff * 0.52).toFixed(1),
          detail: "Dual-banked clients consolidating away from the former Summit relationship as the platforms merge — duplicated mandates and fee-schedule overlap." },
        { factor: "Fee & pricing harmonisation", impact_usd_m: +(diff * 0.28).toFixed(1),
          detail: "Repricing to the unified Apex schedule triggered partial withdrawals among price-sensitive Swiss-booked clients." },
        { factor: "Advisor reassignment", impact_usd_m: +(diff * 0.20).toFixed(1),
          detail: "Relationship-manager changes during migration reduced engagement and prompted balance transfers." },
      ]
    : isApac
    ? [
        { factor: "New-client acquisition", impact_usd_m: +(diff * 0.49).toFixed(1),
          detail: "Onboarding of UHNW entrepreneurs in Hong Kong & Singapore following the integrated APAC platform launch." },
        { factor: "Mandate up-tiering", impact_usd_m: +(diff * 0.31).toFixed(1),
          detail: "Existing clients moving from advisory into discretionary and private-markets mandates." },
        { factor: "FX / market tailwind", impact_usd_m: +(diff * 0.20).toFixed(1),
          detail: "Favourable currency moves and equity performance lifted reported flows for the cohort." },
      ]
    : [
        { factor: "Allocation shift", impact_usd_m: +(diff * 0.46).toFixed(1),
          detail: "Net reallocation between cash and invested mandates within the segment." },
        { factor: "Seasonality", impact_usd_m: +(diff * 0.30).toFixed(1),
          detail: "Recurring half-year funding/liquidity pattern typical for this cohort." },
        { factor: "Pricing & engagement", impact_usd_m: +(diff * 0.24).toFixed(1),
          detail: "Changes in fee sensitivity and advisor contact frequency over the period." },
      ];

  const narrative = down
    ? `**${d.label}** ${metric === "outflow" ? "outflows rose" : "flows fell"} from $${Math.abs(d.metric_reference_usd_m)}m to $${Math.abs(d.metric_interest_usd_m)}m over the recent six months (${(d.relative_difference * 100).toFixed(1)}%), about $${Math.abs(d.unexpected_difference_usd_m)}m worse than the bankwide trend would predict. The move is driven mainly by ${factors[0].factor.toLowerCase()}${isDual ? " — the classic post-merger consolidation risk where clients who held both Apex and Summit relationships rationalise down to one provider" : ""}. This is a controllable, relationship-led decline rather than a market effect, which is why it warrants direct intervention.`
    : `**${d.label}** ${metric === "outflow" ? "outflows" : "flows"} grew from $${d.metric_reference_usd_m}m to $${d.metric_interest_usd_m}m (${(d.relative_difference * 100).toFixed(1)}%), roughly $${d.unexpected_difference_usd_m}m above the bankwide trend. The uplift is led by ${factors[0].factor.toLowerCase()}${isApac ? ", reflecting the integrated APAC platform gaining share in the fastest-growing wealth pool" : ""}. Protecting and replicating this momentum is the priority.`;

  const prevention = down
    ? [
        { title: isDual ? "Launch a dual-banked retention sprint" : "Targeted retention outreach",
          detail: isDual
            ? "Auto-enrol every dual-banked client in this segment into the Flight-Risk Sentinel save-play queue; senior-advisor calls within 10 business days, consolidated cross-bank pricing on the table."
            : "Prioritise advisor outreach to the highest-balance accounts in this segment with a portfolio health-check offer.",
          owner: "Regional Market Head" },
        { title: "Pre-empt fee-driven attrition",
          detail: "Apply grandfathered or blended pricing for migrating clients for 12 months; flag any repricing >15bps for relationship-manager review before it lands.",
          owner: "Pricing & Revenue Mgmt" },
        { title: "Stabilise relationship continuity",
          detail: "Freeze advisor reassignments for at-risk dual-banked clients during migration; assign a named transition contact per household.",
          owner: "COO / Integration Office" },
        { title: "Add an early-warning monitor",
          detail: "Stand up a weekly AI.KEY_DRIVERS + attrition watch on this segment so an unexpected-difference breach pages the desk before the quarter closes.",
          owner: "Data & Analytics" },
      ]
    : [
        { title: "Codify and scale the winning play",
          detail: "Document the acquisition + up-tiering motion behind this cohort and roll it out to comparable segments in adjacent booking centres.",
          owner: "Regional Market Head" },
        { title: "Protect the gains",
          detail: "Lock in newly onboarded UHNW clients with onboarding-plus journeys and private-markets access before competitors respond.",
          owner: "Product & Advisory" },
        { title: "Reinforce capacity",
          detail: "Ensure advisor and booking-centre capacity keeps pace with the inflow so service quality does not dilute the momentum.",
          owner: "COO" },
      ];

  const good = (d.direction === "up") === (metric !== "outflow");
  const sql = kdSqlBlock(metric, d.segment, d.metric_interest_usd_m, d.metric_reference_usd_m, good);

  return {
    metric, metric_label: t.label, label: d.label, segment: d.segment, direction: d.direction,
    what_happened: {
      recent_usd_m: d.metric_interest_usd_m, prior_usd_m: d.metric_reference_usd_m,
      difference_usd_m: d.difference_usd_m, relative_difference: d.relative_difference,
      unexpected_difference_usd_m: d.unexpected_difference_usd_m,
      contribution: d.contribution, apriori_support: d.apriori_support, trend,
      ai_function: "AI.DETECT_ANOMALIES", sql: sql.anomalies,
    },
    rca: { narrative, factors, ai_function: "AI.KEY_DRIVERS", sql: sql.drivers },
    whats_next: {
      forecast,
      commentary: down
        ? `Left unmanaged, ${d.label} stays below trend through H2 — an estimated $${Math.abs(forecast.reduce((s, f) => s + f.yhat, 0)).toFixed(0)}m over the next six months, widening confidence bands as attrition compounds. The retention actions below are modelled to arrest and reverse the slide.`
        : `On current trajectory ${d.label} continues above trend into H2, contributing an estimated $${forecast.reduce((s, f) => s + f.yhat, 0).toFixed(0)}m over the next six months — a meaningful step toward the $200bn NNA ambition if capacity keeps pace.`,
      ai_function: "AI.FORECAST", sql: sql.forecast,
    },
    prevention: { actions: prevention, ai_function: "AI.GENERATE", sql: sql.prevention },
  };
}

const NAMES = ["Hans Müller", "Marie Dubois", "Luca Rossi", "Sophie Favre",
  "Wei Chen", "Anya Keller", "Pierre Moreau", "Elena Bernasconi",
  "Maximilian Weber", "Chiara Tan", "Johan Brunner", "Priya Lim"];
const SEG = ["Affluent", "HNW", "UHNW", "Family Office", "Institutional"];
const CENTRES = ["Zurich", "Geneva", "London", "New York", "Hong Kong", "Singapore"];

const BANKS = ["summit|apex", "apex", "summit"];
export const mockClients: ClientHit[] = NAMES.map((n, i) => ({
  client_id: `CLI_${String(i).padStart(7, "0")}`,
  full_name: n,
  segment_tier: SEG[i % SEG.length],
  booking_centre: CENTRES[i % CENTRES.length],
  total_aum_usd: [1.2e6, 1.4e7, 1.2e8, 8e8, 1.5e9][i % 5] * (0.5 + (i % 4) / 2),
  source_banks: BANKS[i % 3],
  dual_banked: i % 3 === 0,
}));

export const mock = {
  kpis: (): Kpis => ({
    clients: 40000, aum_usd_bn: 2114.5, accounts: 92626, dual_banked_pct: 21.7,
    advisors: 900, nna_ytd_usd_m: 18420, er_accuracy: 96.4, cross_sell_opportunity: 31304,
  }),
  sources: (): Source[] => [
    { bank: "Apex Bank", entity: "Client master", format: "CSV", rows: 24321, status: "mapped" },
    { bank: "Apex Bank", entity: "Portfolios", format: "FIXED_WIDTH", rows: 36459, status: "mapped" },
    { bank: "Apex Bank", entity: "Positions", format: "PARQUET", rows: 243447, status: "mapped" },
    { bank: "Apex Bank", entity: "Advisors", format: "XLSX", rows: 416, status: "mapped" },
    { bank: "Summit Bank", entity: "Client master", format: "JSON", rows: 24375, status: "mapped" },
    { bank: "Summit Bank", entity: "Accounts", format: "XML", rows: 48781, status: "mapped" },
    { bank: "Summit Bank", entity: "Transactions", format: "NDJSON", rows: 281135, status: "mapped" },
  ],
  unify: (): UnifyResult => ({
    mapped_fields: 142, dual_banked_clusters: 8696, accuracy: 96.4,
    before: {
      _source: "summit / summit_clients.json", cifNumber: "Summit000128844",
      client: { displayName: "MÜLLER, H.", clientSegment: "UHNW", dateOfBirth: "1968-04-12" },
      address: { country: "CH" }, booking: { baseCcy: "CHF" },
    },
    after: {
      client_id: "CLI_0001288", full_name: "Hans Müller", segment_tier: "UHNW",
      domicile: "Switzerland", source_banks: ["summit", "apex"], dual_banked: true,
      total_aum_usd: 134200000,
    },
  }),
  clientSearch: (q: string): ClientHit[] =>
    mockClients.filter((c) => c.full_name.toLowerCase().includes(q.toLowerCase())) .length
      ? mockClients.filter((c) => c.full_name.toLowerCase().includes(q.toLowerCase()))
      : mockClients,
  nba: (cid: string): NbaResult => ({
    client: mockClients.find((c) => c.client_id === cid) ?? mockClients[2],
    graph: {
      nodes: [
        { id: cid, label: "This client", type: "client" },
        { id: "HH", label: "Household", type: "household" },
        { id: "M1", label: "Household member", type: "client" },
        { id: "M2", label: "Household member", type: "client" },
        { id: "A1", label: "Discretionary", type: "account" },
        { id: "A2", label: "Lombard", type: "account" },
        { id: "ADV", label: "R. Brunner (CA)", type: "advisor" },
      ],
      edges: [
        { source: cid, target: "HH", label: "BELONGS_TO" },
        { source: "M1", target: "HH", label: "BELONGS_TO" },
        { source: "M2", target: "HH", label: "BELONGS_TO" },
        { source: cid, target: "A1", label: "HOLDS" },
        { source: cid, target: "A2", label: "HOLDS" },
        { source: cid, target: "ADV", label: "ADVISED_BY" },
      ],
    },
    actions: [
      { product: "Private Markets Access Programme", score: 0.91,
        signals: ["2 household members hold private markets", "UHNW look-alike cohort"],
        rationale: "The household holds significant private-markets exposure while this client does not — a private-markets sleeve aligns with their risk profile and the household's allocation pattern." },
      { product: "Wealth Planning & Succession Advisory", score: 0.78,
        signals: ["Family-office linkage", "Multi-generational household"],
        rationale: "Household structure suggests succession-planning needs not yet served." },
      { product: "Sustainable Investing Discretionary Mandate", score: 0.66,
        signals: ["Look-alike clients adopting ESG mandates"],
        rationale: "Behaviourally similar clients increasingly hold sustainable mandates." },
    ],
    cross_platform: {
      home_platform: "Apex Bank", other_platform: "Summit Bank",
      recommendations: [
        { product: "Capital Protection Structured Solutions", product_type: "structured", origin_platform: "Summit Bank",
          rationale: "A Summit Bank-originated structured solution, now available post-integration, offering defined downside protection suited to this client's risk profile." },
        { product: "Lombard Credit Facility", product_type: "lombard", origin_platform: "Summit Bank",
          rationale: "Securities-backed lending — a Summit Bank strength now on the unified shelf — can unlock liquidity without liquidating the portfolio." },
      ],
    },
  }),
  nbaDraft: (cid: string, product: string) => {
    const c = mockClients.find((x) => x.client_id === cid) ?? mockClients[2];
    const first = c.full_name.split(" ")[0];
    return {
      product, client: c.full_name,
      note: `Dear ${first},\n\nAs we bring your Apex Bank and Summit Bank relationships together, I've been reviewing your portfolio and believe the ${product} could be a strong fit for your objectives. Several members of your household already benefit from it. I'd welcome a brief call to walk through how it works and share our latest CIO views — no obligation.\n\nWarm regards,\nYour Apex advisor`,
    };
  },
  retentionPipeline: () =>
    Array.from({ length: 12 }, (_, w) => {
      const count = 40 + ((w * 37) % 80);
      return { week: `2026-W${24 + w}`, count, high_risk: Math.round(count * 0.3) };
    }),
  retentionScores: (): RetentionScore[] =>
    // dual-banked clients dominate the top of the flight-risk list (the integration story)
    [...mockClients].sort((a, b) => Number(b.dual_banked) - Number(a.dual_banked)).slice(0, 12).map((c, i) => ({
      client_id: c.client_id, full_name: c.full_name, segment_tier: c.segment_tier,
      flight_risk: Math.max(0.2, 0.93 - i * 0.05),
      drivers: c.dual_banked ? ["Dual-banked (Apex + Summit)", "Recent net outflows"] : ["Fee sensitivity", "KYC review pending"],
      play: `Relationship review + tailored mandate proposal for ${c.full_name}; offer a CIO portfolio health-check and discuss consolidated pricing.`,
      source_banks: c.source_banks, dual_banked: c.dual_banked,
    })),
  retentionCampaign: (clientId: string): any => {
    const c = mockClients.find((x) => x.client_id === clientId) ?? mockClients[2];
    const dual = c.total_aum_usd > 5e7;
    const drivers = dual ? ["Dual-banked (Apex Bank + Summit Bank)", "Net outflows over the last 6 months"] : ["Fee sensitivity", "Reduced transaction velocity"];
    return {
      client: { client_id: c.client_id, full_name: c.full_name, segment_tier: c.segment_tier, region: (c as any).region ?? "Switzerland", booking_centre: c.booking_centre, risk_profile: "Balanced", total_aum_usd: c.total_aum_usd, tenure_days: 3650, dual_banked: dual },
      flight_risk: 0.82, drivers,
      context: {
        asset_mix: [{ asset_class: "equity", pct: 48 }, { asset_class: "fixed_income", pct: 22 }, { asset_class: "cash", pct: 18 }, { asset_class: "alternative", pct: 12 }],
        household_whitespace: [{ product: "discretionary", household_signal: 3 }, { product: "alternative", household_signal: 2 }],
        recent_net_flow_usd: -2400000, advisor: { name: "R. Brunner", desk: "UHNW & Family Office" }, flight_risk: 0.82,
      },
      campaign: {
        objective: `Retain ${c.full_name} and reverse recent outflows by deepening the relationship.`,
        retention_offer: "Complimentary CIO portfolio health-check + consolidated cross-bank pricing review.",
        next_best_action: "Introduce a discretionary mandate (held by household members) to capture idle cash.",
        preferred_channel: "Senior advisor call, followed by an in-person review",
        talking_points: [
          "Acknowledge the Summit Bank integration and reassure on continuity of service",
          "18% idle cash could be deployed into a discretionary mandate",
          "Household members already hold discretionary & alternatives — offer parity",
          "Consolidated pricing to address fee sensitivity",
        ],
        email_subject: "Bringing your Apex Bank & Summit Bank relationships together — a portfolio review",
        email_body: `Dear ${c.full_name.split(" ")[0]},\n\nAs we complete the integration of Apex Bank and Summit Bank, I wanted to reach out personally to ensure your portfolio is working as hard as it can for you. I've noticed a meaningful cash balance we could put to work, and several solutions your wider household already benefits from that may suit your objectives. I'd welcome a short call to share our latest CIO views and a consolidated view of your relationships.\n\nWarm regards,\nR. Brunner, Apex Bank`,
      },
    };
  },
  forecast: (metric: string): ForecastResult => {
    const base = { nna: 22, aum: 780, revenue: 2.3 }[metric] ?? 50;
    let v = base;
    const history = Array.from({ length: 36 }, (_, t) => {
      v *= 1 + (((t * 7) % 5) - 1) / 200;
      return { ts: `M${t + 1}`, yhat: +v.toFixed(2), actual: +v.toFixed(2) };
    });
    let last = v;
    const forecast = Array.from({ length: 12 }, (_, t) => {
      last *= 1 + ((t % 3) + 1) / 150;
      const s = last * 0.06;
      return { ts: `F${t + 1}`, yhat: +last.toFixed(2), lo: +(last - s).toFixed(2), hi: +(last + s).toFixed(2) };
    });
    return { metric, history, forecast,
      commentary: `${metric.toUpperCase()} is projected to grow steadily over the next 12 months, with momentum strongest in APAC and GWM — consistent with the $200bn net-new-money ambition. Confidence bands widen beyond month six.` };
  },
  keyDrivers: (metric: string): KeyDriversResult => kdResult(metric),
  keyDriverDrilldown: (metric: string, label: string): DriverDrilldown => kdDrilldown(metric, label),
  research: (q: string): DocHit[] => [
    { document_id: "DOC_000012", title: "Apex CIO Research — Private credit allocation for UHNW portfolios", doc_type: "cio_research", snippet: "Our CIO view favours a structural allocation to private credit for qualified UHNW and family-office clients, citing attractive risk-adjusted yields…", score: 0.92, gcs_uri: "gs://fsi_pov/raw/documents/DOC_000012.pdf" },
    { document_id: "DOC_000044", title: "Apex CIO Research — Global asset allocation: balanced positioning into 2026", doc_type: "cio_research", snippet: "Our balanced multi-asset stance holds a modest overweight to global equities funded from cash, neutral duration in high-grade bonds…", score: 0.85, gcs_uri: "gs://fsi_pov/raw/documents/DOC_000044.pdf" },
    { document_id: "DOC_000133", title: "Apex CIO Research — APAC wealth: capturing the next decade", doc_type: "cio_research", snippet: "Asia-Pacific remains the fastest-growing wealth pool. We highlight onshore and offshore booking considerations and currency hedging…", score: 0.78, gcs_uri: "gs://fsi_pov/raw/documents/DOC_000133.pdf" },
  ],
  researchAnswer: (q: string) => ({
    answer: "Per the latest CIO research, a 5–12% allocation to private credit is recommended for qualified UHNW and family-office clients, funded from public high yield and phased over 12–18 months via diversified direct-lending and secondaries vehicles [DOC_000012]. Liquidity terms and J-curve management are key considerations.",
    citations: [
      { document_id: "DOC_000012", title: "Private credit allocation for UHNW portfolios", gcs_uri: "gs://fsi_pov/raw/documents/DOC_000012.pdf" },
    ],
  }),
  segments: (): Segment[] => [
    { id: 0, label: "Globally-Mobile UHNW Entrepreneurs", size: 6200, avg_aum_usd: 1.4e8, dominant_asset: "equity", attrition_index: 0.31, dual_banked_pct: 38 },
    { id: 1, label: "Conservative Swiss Retirees", size: 8900, avg_aum_usd: 3.2e6, dominant_asset: "fixed_income", attrition_index: 0.12, dual_banked_pct: 12 },
    { id: 2, label: "Multi-Generational Family Offices", size: 2100, avg_aum_usd: 6.8e8, dominant_asset: "alternative", attrition_index: 0.18, dual_banked_pct: 41 },
    { id: 3, label: "APAC Growth Seekers", size: 5400, avg_aum_usd: 2.1e7, dominant_asset: "equity", attrition_index: 0.27, dual_banked_pct: 27 },
    { id: 4, label: "Sustainable-Focused Affluent", size: 7300, avg_aum_usd: 1.9e6, dominant_asset: "fund", attrition_index: 0.15, dual_banked_pct: 15 },
    { id: 5, label: "Structured-Yield Income Clients", size: 4100, avg_aum_usd: 1.1e7, dominant_asset: "structured", attrition_index: 0.22, dual_banked_pct: 22 },
    { id: 6, label: "Institutional Mandates", size: 1200, avg_aum_usd: 1.5e9, dominant_asset: "fixed_income", attrition_index: 0.09, dual_banked_pct: 9 },
    { id: 7, label: "Lombard-Active Liquidity Users", size: 3000, avg_aum_usd: 4.2e7, dominant_asset: "cash", attrition_index: 0.34, dual_banked_pct: 34 },
  ],
  network: () => ({
    anomalies: [
      { type: "Structuring / Smurfing", severity: "high", summary: "12 sub-threshold transfers (USD 9.0k–9.9k) funnelled from 5 retail accounts into one collector account within 9 days." },
      { type: "UBO Risk", severity: "high", summary: "Retail inflows map upstream to an SPV in a high-risk jurisdiction whose ultimate beneficial owner is a flagged Family Office client." },
      { type: "Circular Flow", severity: "medium", summary: "Funds routed A→B→C→A across three booking centres via intermediary proxies, returning ~94% to origin." },
      { type: "Layering", severity: "medium", summary: "Rapid sequential transfers across 6 hops within 48h, each just under internal review limits." },
    ],
    subgraph: {
      nodes: Array.from({ length: 8 }, (_, i) => ({ id: `N${i}`, label: `Account ${i}`, type: "account", risk: ["low", "med", "high"][i % 3] })),
      edges: Array.from({ length: 8 }, (_, i) => ({ source: `N${i}`, target: `N${(i + 1) % 8}`, amount: 9000 + i * 90 })),
    },
  }),
  ask: (_q: string): AskBlock[] => [
    { type: "thinking", text: "Sending your question to the Conversational Analytics data agent…" },
    { type: "thinking", text: "Analyzing context" },
    { type: "thinking", text: "Retrieved context for 31 tables" },
    { type: "thinking", text: "Generated BigQuery SQL — running it…" },
    { type: "text", text: "Across booking centres, **Hong Kong** and **Singapore** posted the fastest net-new-money growth last quarter, with APAC GWM leading the bank. Switzerland remains the largest AuM base." },
    { type: "table", columns: ["booking_centre", "nna_usd_m", "qoq_growth_pct"],
      rows: [["Hong Kong", 2140, 11.4], ["Singapore", 1890, 9.8], ["Zurich", 3120, 4.1], ["Geneva", 1640, 3.7], ["New York", 1430, 5.2], ["London", 1210, 2.9]] },
    { type: "chart", spec: { mark: "bar", x: "booking_centre", y: "nna_usd_m" } },
    { type: "sql", sql: "SELECT booking_centre, ROUND(SUM(net_new_money_usd)/1e6,1) AS nna_usd_m\nFROM `raves-altostrat.FSI_POV.client_flows` f\nJOIN `raves-altostrat.FSI_POV.clients` c USING (client_id)\nWHERE f.month >= '2026-01-01'\nGROUP BY booking_centre ORDER BY nna_usd_m DESC" },
  ],
  agentLifecycle: (goal: string): any[] => {
    const g = goal.toLowerCase();
    const dfUrl = "https://console.cloud.google.com/bigquery/dataform/locations/us-central1/repositories/fsi_pov_pipeline/workspaces/dev?project=raves-altostrat";
    const bq = (table: string, kind = "table") => ({ label: table, ref: `raves-altostrat.FSI_POV.${table}`, kind, url: `https://console.cloud.google.com/bigquery?project=raves-altostrat&ws=!1m5!1m4!4m3!1sraves-altostrat!2sFSI_POV!3s${table}` });
    let ds: any, caq: string, caBlocks: any[];
    if (/(lose|attrition|churn|flight|retain|outflow)/.test(g)) {
      ds = { kind: "retention", scores: mock.retentionScores().slice(0, 8), headline: "Scored every client with the BQML attrition model; flagged the highest flight-risk cohort.", artifacts: [bq("attrition_model", "model"), bq("attrition_scores")] };
      caq = "How many clients are dual-banked, broken down by booking centre?";
      caBlocks = [{ type: "text", text: "Dual-banked clients are concentrated in **Zurich**, **Geneva** and **Hong Kong** — the integration overlap is highest there." }, { type: "table", columns: ["booking_centre", "dual_banked"], rows: [["Zurich", 2104], ["Geneva", 1380], ["Hong Kong", 1190], ["London", 980]] }];
    } else if (/(forecast|nna|net new|aum|revenue|grow|project)/.test(g)) {
      const region = /apac|asia|hong kong|singapore/.test(g) ? "APAC"
        : /emea|europe|london/.test(g) ? "EMEA"
        : /americas|new york|\bus\b/.test(g) ? "Americas"
        : /swiss|zurich|geneva/.test(g) ? "Switzerland" : "all regions";
      ds = { kind: "forecast", forecast: mock.forecast("nna"), headline: `Ran AI.FORECAST (TimesFM 2.5) for ${region} — net new money, 12-month horizon.`, artifacts: [bq("forecast_nna"), bq("ts_nna_monthly")] };
      caq = `How has net new money in ${region} trended over the last 12 months — the historical baseline behind this forecast?`;
      caBlocks = [{ type: "text", text: `Net new money in **${region}** grew steadily over the trailing 12 months, accelerating in the last two quarters — consistent with the forecast trajectory.` }, { type: "table", columns: ["quarter", "nna_usd_bn"], rows: [["2025 Q3", 9.1], ["2025 Q4", 9.8], ["2026 Q1", 10.6], ["2026 Q2", 11.4]] }];
    } else {
      ds = { kind: "segments", segments: mock.segments(), headline: "Trained BQML KMEANS (8 clusters), assigned every client, named with Gemini.", artifacts: [bq("client_kmeans", "model"), bq("client_segments"), bq("client_segments_summary")] };
      caq = "What is the average AuM and client count per segment?";
      caBlocks = [{ type: "text", text: "The largest segments by AuM are the **Family Office** and **UHNW equity-led** clusters." }, { type: "table", columns: ["segment", "clients", "avg_aum_usd"], rows: [["Pinnacle Family Office", 5176, 680000000], ["Strategic Equity Partners", 7217, 21000000]] }];
    }
    const purpose: Record<string, string> = {
      raw: "The unified two-bank estate the agents draw from.",
      de: "Prepares the exact data/pipeline this goal needs (on the Dataform workspace).",
      ds: "Builds and runs the model that answers the goal.",
      ca: "Plain-English context behind the result — the same question any business user could ask directly.",
      business: "Turns the model + context into a decision and recommended action.",
    };
    const events: any[] = [
      { type: "persona", id: "raw", title: "Raw Data", status: "working", badge: "two-bank estate" },
      { type: "persona", id: "raw", title: "Raw Data", status: "done", badge: "two-bank estate", output: { kind: "raw", ...mock.rawOverview() } },
      { type: "persona", id: "de", title: "Data Engineering Agent", status: "working", badge: "LIVE A2A · Google" },
      { type: "persona", id: "de", title: "Data Engineering Agent", status: "done", badge: "LIVE A2A · Google", output: { kind: "messages", workspace_url: dfUrl, messages: ["Analyzing the pipeline…", "The table `client_features` is built from the following source tables: accounts, clients, holdings, transactions."] } },
      { type: "persona", id: "ds", title: "Data Scientist", status: "working", badge: "BigQuery ML" },
      { type: "persona", id: "ds", title: "Data Scientist", status: "done", badge: "BigQuery ML", output: ds },
      { type: "persona", id: "ca", title: "Conversational Analytics Agent", status: "working", badge: "LIVE · Gemini Data Analytics" },
      { type: "persona", id: "ca", title: "Conversational Analytics Agent", status: "done", badge: "LIVE · Gemini Data Analytics", output: { kind: "ca", question: caq, blocks: caBlocks } },
      { type: "persona", id: "business", title: "Business User", status: "working", badge: "decision" },
      { type: "persona", id: "business", title: "Business User", status: "done", badge: "decision", output: { kind: "text", text: "Prioritise the highest-value, highest-risk cohorts: direct advisor outreach where flight-risk is elevated and cross-sell where household whitespace exists — protecting AuM and advancing the $200bn net-new-money ambition." } },
      { type: "done" },
    ];
    return events.map((e) => (e.id ? { ...e, purpose: purpose[e.id] } : e));
  },
  rawOverview: () => ({
    sources: [
      { name: "Apex Bank — raw clients (CSV)", rows: 24321 },
      { name: "Summit Bank — raw clients (JSON)", rows: 24375 },
      { name: "Resolved Client 360", rows: 40000 },
    ],
    dual_banked: 8696,
    sample: [
      { client_id: "CLI_0001288", full_name: "Hans Müller", segment_tier: "UHNW", source_banks: "summit|apex", dual_banked: true },
      { client_id: "CLI_0009934", full_name: "Wei Chen", segment_tier: "UHNW", source_banks: "summit|apex", dual_banked: true },
      { client_id: "CLI_0004102", full_name: "Sophie Favre", segment_tier: "Family Office", source_banks: "apex", dual_banked: false },
    ],
  }),
  agentSteps: (goal: string): AgentStep[] => {
    const g = goal.toLowerCase();
    const bq = (table: string, kind = "table") => ({
      label: table, ref: `raves-altostrat.FSI_POV.${table}`, kind,
      url: `https://console.cloud.google.com/bigquery?project=raves-altostrat&ws=!1m5!1m4!4m3!1sraves-altostrat!2sFSI_POV!3s${table}`,
    });
    const dataform = { label: "Dataform workspace (Data Engineering Agent)", ref: "fsi_pov_pipeline/dev", kind: "dataform", url: "https://console.cloud.google.com/bigquery/dataform/locations/us-central1/repositories/fsi_pov_pipeline/workspaces/dev?project=raves-altostrat" };
    if (/(segment|cluster|persona|group)/.test(g))
      return [
        { type: "step", agent: "orchestrator", skill: "route_goal", detail: "Decomposed goal and selected the 'segments' workflow.", tool_calls: ["ADK: classify_intent"], a2a: "→ data_engineering, data_scientist" },
        { type: "step", agent: "data_engineering", skill: "build_feature_table", real: true, detail: "The table client_features is built from the following source tables: accounts, clients, holdings, transactions.", tool_calls: ["A2A → geminidataanalytics: dataengineeringagent", "Dataform workspace fsi_pov_pipeline/dev"], a2a: "LIVE A2A · Google Data Engineering Agent" },
        { type: "step", agent: "data_scientist", skill: "segment_clients", detail: "Trained BQML KMEANS (BigFrames engine), assigned every client a segment, named clusters with Gemini.", tool_calls: ["CREATE MODEL client_kmeans (KMEANS)", "ML.PREDICT", "Gemini: name_segments"] },
        { type: "step", agent: "orchestrator", skill: "compose_answer", detail: "Aggregated specialist results.", tool_calls: ["ADK: compose"], a2a: "← data_engineering, data_scientist" },
        { type: "final", result: { type: "segments", segments: mock.segments(), artifacts: [bq("client_kmeans", "model"), bq("client_features"), bq("client_segments"), bq("client_segments_summary"), dataform] } },
      ];
    if (/(lose|attrition|churn|flight|retain|outflow)/.test(g))
      return [
        { type: "step", agent: "orchestrator", skill: "route_goal", detail: "Decomposed goal and selected the 'attrition' workflow. Delegating over A2A.", tool_calls: ["ADK: classify_intent"], a2a: "→ data_engineering, data_scientist" },
        { type: "step", agent: "data_scientist", skill: "score_attrition", detail: "Need engineered features — requesting them from the Data Engineering Agent over A2A.", a2a: "A2A task → data_engineering.build_feature_table" },
        { type: "step", agent: "data_engineering", skill: "build_feature_table", detail: "Built the attrition feature table (tenure, AuM trend, outflow ratio, dual-banked, KYC) and returned the handle.", tool_calls: ["BigQuery: CREATE TABLE attrition_scoring"], a2a: "A2A result → data_scientist" },
        { type: "step", agent: "data_scientist", skill: "score_attrition", detail: "Scored clients with the attrition model (TabularFM / boosted-tree).", tool_calls: ["BigQuery: ML.PREDICT(attrition_model)"] },
        { type: "step", agent: "data_scientist", skill: "explain_drivers", detail: "Extracted top drivers and drafted retention plays.", tool_calls: ["ML.FEATURE_IMPORTANCE", "Gemini: draft_play"] },
        { type: "step", agent: "orchestrator", skill: "compose_answer", detail: "Aggregated specialist results.", tool_calls: ["ADK: compose"], a2a: "← data_engineering, data_scientist" },
        { type: "final", result: { type: "retention", scores: mock.retentionScores().slice(0, 6), artifacts: [bq("attrition_model", "model"), bq("attrition_scores"), bq("attrition_scoring")] } },
      ];
    return [
      { type: "step", agent: "orchestrator", skill: "route_goal", detail: "Decomposed goal and selected the 'forecast' workflow.", tool_calls: ["ADK: classify_intent"], a2a: "→ data_engineering, data_scientist" },
      { type: "step", agent: "data_engineering", skill: "build_feature_table", detail: "Materialised the monthly NNA time-series mart by division × region.", tool_calls: ["BigQuery: ts_nna_monthly"], a2a: "A2A result → data_scientist" },
      { type: "step", agent: "data_scientist", skill: "forecast_series", detail: "Ran AI.FORECAST (TimesFM 2.5) — zero-training, multi-series — for a 12-month horizon.", tool_calls: ["BigQuery: AI.FORECAST(TimesFM 2.5)"] },
      { type: "step", agent: "data_scientist", skill: "explain_drivers", detail: "Narrated drivers against the $200bn NNA ambition.", tool_calls: ["Gemini: narrate"] },
      { type: "step", agent: "orchestrator", skill: "compose_answer", detail: "Aggregated specialist results.", tool_calls: ["ADK: compose"], a2a: "← data_engineering, data_scientist" },
      { type: "final", result: { type: "forecast", forecast: mock.forecast("nna"), artifacts: [bq("forecast_nna"), bq("ts_nna_monthly")] } },
    ];
  },
};
