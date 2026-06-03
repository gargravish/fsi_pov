export interface Kpis {
  clients: number;
  aum_usd_bn: number;
  accounts: number;
  dual_banked_pct: number;
  advisors: number;
  nna_ytd_usd_m: number;
  er_accuracy: number;
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
export interface NbaResult {
  client: any;
  graph: GraphData;
  actions: NbaAction[];
}
export interface RetentionScore {
  client_id: string;
  full_name: string;
  segment_tier: string;
  flight_risk: number;
  drivers: string[];
  play: string;
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
