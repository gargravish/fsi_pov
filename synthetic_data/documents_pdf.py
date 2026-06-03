"""
documents_pdf.py — Generate wealth-management documents as PDFs (CIO research,
KYC profiles, suitability assessments, advice notes) + a manifest CSV carrying
the body text. PDFs land in GCS for AI.PARSE_DOCUMENT; the manifest text feeds
autonomous embeddings + AI.SEARCH (Research Brain).

Uses reportlab. Body text is templated (deterministic, offline-safe); set
GEMINI_API_KEY to optionally enrich with Gemini.
"""
from __future__ import annotations

import csv
import os
import random
import textwrap

from config import MASTER_SEED, N_DOCUMENTS, DOC_TYPES, DOC_TYPE_WEIGHTS, docs_output_dir

_rng = random.Random(MASTER_SEED ^ 0xD0C5)

_CIO_TOPICS = [
    ("Private credit allocation for UHNW portfolios",
     "Our CIO view favours a structural allocation to private credit for qualified "
     "UHNW and family-office clients, citing attractive risk-adjusted yields, floating-rate "
     "protection against rate volatility, and diversification away from public-market beta. "
     "We recommend a 5-12% sleeve funded from public high yield, phased over 12-18 months "
     "via diversified direct-lending and secondaries vehicles, with attention to liquidity "
     "terms and J-curve management."),
    ("Swiss equities and the franc outlook",
     "We remain constructive on Swiss large-cap quality compounders given resilient earnings, "
     "strong balance sheets and defensive sector mix. A firm franc is a headwind for exporters "
     "but supports import-sensitive domestics; we favour healthcare and staples leaders and stay "
     "selective on financials."),
    ("Global asset allocation: balanced positioning into 2026",
     "Our balanced multi-asset stance holds a modest overweight to global equities funded from "
     "cash, a neutral duration position in high-grade bonds, and a diversifying allocation to "
     "alternatives including gold and macro hedge strategies. We see selective EM and AI-capex "
     "beneficiaries as key sources of return."),
    ("Sustainable investing: integrating ESG into core mandates",
     "We outline how sustainability objectives can be integrated into discretionary mandates "
     "without sacrificing diversification, using best-in-class tilts, thematic baskets in clean "
     "energy and circular economy, and engagement-led active ownership."),
    ("APAC wealth: capturing the next decade of growth",
     "Asia-Pacific remains the fastest-growing wealth pool. We highlight onshore and offshore "
     "booking considerations, currency hedging for USD-referenced portfolios, and structured "
     "yield-enhancement solutions tailored to entrepreneurial first-generation wealth."),
]


def _para(text: str) -> str:
    return text


def _doc_text(doc_type: str, client_id: str | None) -> tuple[str, str]:
    """Return (title, body)."""
    if doc_type == "cio_research":
        title, body = _rng.choice(_CIO_TOPICS)
        return f"UBS CIO Research — {title}", body
    if doc_type == "kyc":
        sow = _rng.choice(["entrepreneurial business sale", "inherited family wealth",
                           "executive compensation", "real-estate portfolio",
                           "professional practice"])
        pep = _rng.choice(["negative", "flagged for review"])
        edd = _rng.choice(["not required", "completed", "pending"])
        title = f"Know-Your-Client Profile — {client_id}"
        body = (
            f"Client {client_id} onboarded through the wealth-management division. "
            f"Source of wealth: {sow}. Risk classification reviewed; PEP screening {pep}; "
            f"sanctions screening clear. Expected activity consistent with declared profile. "
            f"Enhanced due diligence {edd}."
        )
        return title, body
    if doc_type == "suitability":
        obj = _rng.choice(["capital growth", "income", "capital preservation",
                           "balanced growth and income"])
        ke = _rng.choice(["advanced", "good", "moderate"])
        cap = _rng.choice(["10%", "15%", "20%"])
        title = f"Suitability Assessment — {client_id}"
        body = (
            f"Investment objective: {obj}. Knowledge and experience assessed as {ke}. "
            f"Proposed mandate aligns with the client's risk tolerance and time horizon; "
            f"concentration and liquidity risks discussed. Structured products limited to "
            f"{cap} of the portfolio."
        )
        return title, body
    # advice_note
    sleeve = _rng.choice(["private markets", "sustainable equity", "short-duration credit"])
    title = f"Advice Note — {client_id}"
    body = (
        f"Following the portfolio review, we discussed rebalancing toward the strategic asset "
        f"allocation, trimming concentrated single-stock exposure, and introducing a {sleeve} "
        f"sleeve. Client agreed to proceed with a phased implementation and a follow-up review "
        f"next quarter."
    )
    return title, body


def generate(clients: list[dict]) -> list[dict]:
    """Generate PDFs + return manifest rows."""
    out_dir = docs_output_dir()
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
        have_rl = True
    except Exception:
        have_rl = False

    client_ids = [c["client_id"] for c in clients]
    manifest: list[dict] = []
    for i in range(N_DOCUMENTS):
        dtype = _rng.choices(DOC_TYPES, weights=DOC_TYPE_WEIGHTS, k=1)[0]
        cid = None if dtype == "cio_research" else _rng.choice(client_ids)
        title, body = _doc_text(dtype, cid)
        doc_id = f"DOC_{i:06d}"
        fname = f"{doc_id}.pdf"
        fpath = os.path.join(out_dir, fname)

        if have_rl:
            c = canvas.Canvas(fpath, pagesize=A4)
            width, height = A4
            c.setFont("Helvetica-Bold", 14)
            c.drawString(2 * cm, height - 2.5 * cm, title[:90])
            c.setFont("Helvetica", 10)
            y = height - 3.6 * cm
            for line in textwrap.wrap(body, width=95):
                c.drawString(2 * cm, y, line)
                y -= 0.5 * cm
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(2 * cm, 1.5 * cm,
                         "UBS Helix POV — synthetic document. Not investment advice.")
            c.save()
        else:
            # fallback: write a .txt so the pipeline still works without reportlab
            fpath = fpath.replace(".pdf", ".txt")
            fname = fname.replace(".pdf", ".txt")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(title + "\n\n" + body)

        manifest.append({
            "document_id": doc_id,
            "gcs_uri": f"raw/documents/{fname}",  # prefix completed at upload
            "doc_type": dtype,
            "client_id": cid or "",
            "title": title,
            "parsed_text": body,
        })

    # write manifest
    mpath = os.path.join(out_dir, "document_manifest.csv")
    with open(mpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0].keys()))
        w.writeheader()
        w.writerows(manifest)
    return manifest
