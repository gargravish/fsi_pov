import { mock } from "./mock";
import type {
  Kpis, Source, UnifyResult, ClientHit, NbaResult, RetentionScore,
  ForecastResult, DocHit, Segment, AgentStep, AskBlock,
} from "./types";

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "false";
const BASE = import.meta.env.VITE_API_BASE ?? "";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}
async function post<T>(path: string, body: any): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export const api = {
  kpis: (): Promise<Kpis> => (USE_MOCKS ? Promise.resolve(mock.kpis()) : get("/api/kpis")),
  sources: (): Promise<Source[]> => (USE_MOCKS ? Promise.resolve(mock.sources()) : get("/api/sources")),
  unify: (): Promise<UnifyResult> => (USE_MOCKS ? Promise.resolve(mock.unify()) : post("/api/unify/run", {})),
  clientSearch: (q: string): Promise<ClientHit[]> =>
    USE_MOCKS ? Promise.resolve(mock.clientSearch(q)) : get(`/api/clients/search?q=${encodeURIComponent(q)}`),
  nba: (cid: string): Promise<NbaResult> => (USE_MOCKS ? Promise.resolve(mock.nba(cid)) : get(`/api/nba/${cid}`)),
  retentionPipeline: (): Promise<{ week: string; count: number; high_risk: number }[]> =>
    USE_MOCKS ? Promise.resolve(mock.retentionPipeline()) : get("/api/retention/pipeline"),
  retentionScores: (): Promise<RetentionScore[]> =>
    USE_MOCKS ? Promise.resolve(mock.retentionScores()) : get("/api/retention/scores"),
  retentionCampaign: (clientId: string): Promise<any> =>
    USE_MOCKS ? Promise.resolve(mock.retentionCampaign(clientId)) : get(`/api/retention/campaign/${clientId}`),
  forecast: (metric: string, division = "all", region = "all"): Promise<ForecastResult> =>
    USE_MOCKS ? Promise.resolve(mock.forecast(metric)) : get(`/api/forecast?metric=${metric}&division=${division}&region=${region}`),
  research: (q: string): Promise<DocHit[]> =>
    USE_MOCKS ? Promise.resolve(mock.research(q)) : get(`/api/research/search?q=${encodeURIComponent(q)}`),
  researchAnswer: (q: string): Promise<any> =>
    USE_MOCKS ? Promise.resolve(mock.researchAnswer(q)) : post("/api/research/answer", { q }),
  segments: (): Promise<Segment[]> => (USE_MOCKS ? Promise.resolve(mock.segments()) : get("/api/segments")),
  network: (): Promise<any> => (USE_MOCKS ? Promise.resolve(mock.network()) : get("/api/network/patterns")),

  // streaming endpoints
  ask: async (q: string, onBlock: (b: AskBlock) => void): Promise<void> => {
    if (USE_MOCKS) {
      for (const b of mock.ask(q)) { await wait(450); onBlock(b); }
      onBlock({ type: "done" });
      return;
    }
    await stream("/api/ask", { q }, (o) => onBlock(o as AskBlock));
  },
  agents: async (goal: string, onEvent: (s: any) => void): Promise<void> => {
    if (USE_MOCKS) {
      for (const s of mock.agentLifecycle(goal)) { await wait(s.status === "working" ? 250 : 900); onEvent(s); }
      return;
    }
    await stream("/api/agents/goal", { goal }, (o) => onEvent(o));
  },
};

async function stream(path: string, body: any, onMsg: (o: any) => void) {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const reader = r.body!.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const p of parts) {
      const line = p.trim();
      if (line.startsWith("data:")) {
        try { onMsg(JSON.parse(line.slice(5).trim())); } catch {}
      }
    }
  }
}
