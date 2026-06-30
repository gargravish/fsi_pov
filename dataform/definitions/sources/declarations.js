// Declare the curated Client 360 + raw two-bank sources + the BQML attrition
// model so the pipeline can ref()/resolve() them. These are produced by
// synthetic_data/make_all.py --gcp, the Unify & Resolve flow, and
// infra/setup_apex_attrition.sql; Dataform expresses the downstream lineage.
const SOURCES = [
  "clients", "accounts", "holdings", "transactions", "client_flows",
  "attrition_scoring", "attrition_model", "ts_nna_monthly",
  "raw_apex_clients", "raw_summit_clients",
];
SOURCES.forEach((name) => declare({ schema: "FSI_POV", name }));
