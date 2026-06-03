// Declare the curated Client 360 + raw two-bank sources + the BQML attrition
// model so the pipeline can ref()/resolve() them. These are produced by
// synthetic_data/make_all.py --gcp, the Unify & Resolve flow, and
// infra/setup_ubs_attrition.sql; Dataform expresses the downstream lineage.
const SOURCES = [
  "clients", "accounts", "holdings", "transactions",
  "attrition_scoring", "attrition_model", "ts_nna_monthly",
  "raw_ubs_clients", "raw_cs_clients",
];
SOURCES.forEach((name) => declare({ schema: "UBS_POV", name }));
