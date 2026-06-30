export interface Kpis {
  clients: number;
  aum_usd_bn: number;
  accounts: number;
  dual_banked_pct: number;
  advisors: number;
  nna_ytd_usd_m: number;
  er_accuracy: number;
  cross_sell_opportunity?: number;
}
export interface Source {
  bank: string;
  entity: string;
  format: string;
  rows: number;
  status: string;
}
export interface UnifyResult {
  mapped_fields: number;
  dual_banked_clusters: number;
  accuracy: number;
  before: Record<string, any>;
  after: Record<string, any>;
}
export interface ClientHit {
  client_id: string;
  full_name: string;
  segment_tier: string;
  booking_centre: string;
  total_aum_usd: number;
  source_banks?: string;
  dual_banked?: boolean;
}
export interface NbaAction {
  product: string;
  score: number;
  signals: string[];
  rationale: string;
}
export interface GraphData {
  nodes: { id: string; label: string; type: string; risk?: string }[];
  edges: { source: string; target: string; label?: string; amount?: number }[];
}
export interface CrossPlatformRec {
  product: string;
  product_type: string;
  origin_platform: string;
  rationale: string;
}
export interface CrossPlatform {
  home_platform?: string;
  other_platform?: string;
  recommendations?: CrossPlatformRec[];
}
export interface NbaResult {
  client: any;
  graph: GraphData;
  actions: NbaAction[];
  cross_platform?: CrossPlatform;
}
export interface RetentionScore {
  client_id: string;
  full_name: string;
  segment_tier: string;
  flight_risk: number;
  drivers: string[];
  play: string;
  source_banks?: string;
  dual_banked?: boolean;
}
export interface ForecastPoint {
  ts: string;
  yhat: number;
  lo?: number;
  hi?: number;
  actual?: number;
}
export interface ForecastResult {
  metric: string;
  history: ForecastPoint[];
  forecast: ForecastPoint[];
  commentary: string;
}
export interface KeyDriver {
  label: string;
  segment: { name: string; value: string }[];
  metric_interest_usd_m: number;
  metric_reference_usd_m: number;
  difference_usd_m: number;
  relative_difference: number;
  unexpected_difference_usd_m: number;
  contribution: number;
  apriori_support: number;
  direction: "up" | "down";
}
export interface KeyDriversResult {
  metric: string;
  metric_label: string;
  direction: "higher" | "lower";
  interest_period: string;
  reference_period: string;
  total_interest_usd_m: number;
  total_reference_usd_m: number;
  net_change_usd_m: number;
  drivers: KeyDriver[];
  commentary: string;
}
export interface TrendPoint {
  ts: string;
  value: number;
  is_anomaly?: boolean;
}
export interface RcaFactor {
  factor: string;
  impact_usd_m: number;
  detail: string;
}
export interface PreventionAction {
  title: string;
  detail: string;
  owner: string;
}
export interface DriverDrilldown {
  metric: string;
  metric_label: string;
  label: string;
  segment: { name: string; value: string }[];
  direction: "up" | "down";
  what_happened: {
    recent_usd_m: number;
    prior_usd_m: number;
    difference_usd_m: number;
    relative_difference: number;
    unexpected_difference_usd_m: number;
    contribution: number;
    apriori_support: number;
    trend: TrendPoint[];
    ai_function: string;
    sql: string;
  };
  rca: { narrative: string; factors: RcaFactor[]; ai_function: string; sql: string };
  whats_next: { forecast: ForecastPoint[]; commentary: string; ai_function: string; sql: string };
  prevention: { actions: PreventionAction[]; ai_function: string; sql: string };
}
export interface DocHit {
  document_id: string;
  title: string;
  doc_type: string;
  snippet: string;
  score: number;
  gcs_uri: string;
}
export interface Segment {
  id: number;
  label: string;
  size: number;
  avg_aum_usd: number;
  dominant_asset: string;
  attrition_index: number;
  dual_banked_pct?: number;
}
export interface AgentStep {
  type: string;
  agent?: string;
  skill?: string;
  detail?: string;
  tool_calls?: string[];
  a2a?: string;
  real?: boolean;
  result?: any;
}

export interface PersonaEvent {
  type: string; // "persona" | "done"
  id?: string; // raw | de | ds | ca | business
  title?: string;
  status?: "working" | "done";
  badge?: string;
  purpose?: string;
  output?: any;
}
export interface AskBlock {
  type: "thinking" | "text" | "table" | "chart" | "sql" | "done";
  text?: string;
  columns?: string[];
  rows?: any[][];
  spec?: any;
  vega?: any;
  sql?: string;
}
