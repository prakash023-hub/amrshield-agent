import streamlit as st
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.clinical_agent.evidence_store import (
    get_active_antibiogram,
    load_case_studies,
    get_live_dashboard_metrics,
    save_hospital_antibiogram,
)
from agents.clinical_agent.guideline_rag import retrieve_clinical_evidence

st.set_page_config(page_title="Evidence & Case Studies", page_icon="📚", layout="wide")

st.markdown("# 📚 Clinical Evidence & Real-World Data")
st.caption("LangChain RAG · WHO GLASS reference antibiogram · Published case studies · Hospital microbiology upload")

st.warning(
    "Reference data from **public WHO GLASS / national surveillance patterns** and **published guidelines**. "
    "Upload your **hospital microbiology antibiogram** (WHONET export) for institution-specific recommendations. "
    "Research prototype — not CDSCO/FDA cleared."
)

t1, t2, t3, t4 = st.tabs(["📊 Antibiogram", "📖 Case Studies", "🔍 RAG Search", "🏥 Microbiology Upload"])

with t1:
    ab = get_active_antibiogram()
    meta = ab.get("meta", {})
    st.markdown(f"### {meta.get('title', 'Antibiogram')}")
    st.markdown(f"**Dataset:** `{meta.get('dataset_id', '—')}` · **Region:** {meta.get('region', 'India')}")
    st.markdown("**Sources:**")
    for s in meta.get("sources", []):
        st.markdown(f"- {s}")
    st.caption(meta.get("citation", ""))

    org = st.selectbox("Organism", list(ab.get("organisms", {}).keys()))
    if org:
        sites = ab["organisms"][org]
        site = st.selectbox("Specimen / site", list(sites.keys()))
        data = sites[site]
        rows = []
        for drug, val in data.items():
            if isinstance(val, dict):
                rows.append({
                    "Drug": drug,
                    "Susceptible %": val.get("susceptibility_pct"),
                    "Resistant %": val.get("resistance_pct"),
                    "Ref isolates (n)": val.get("n_isolates_ref", "—"),
                })
        st.dataframe(rows, use_container_width=True)

    st.info(meta.get("pilot_note", "Upload your hospital antibiogram in the Microbiology Upload tab."))

with t2:
    st.markdown("### Published real-world case studies & policy evidence")
    for cs in load_case_studies():
        with st.expander(f"**{cs['title']}** — _{cs['source']}_"):
            st.markdown(f"**Setting:** {cs['setting']}")
            st.markdown(cs["summary"])
            st.success(f"**Clinical lesson:** {cs['clinical_lesson']}")
            st.markdown(f"**Intervention:** {cs['intervention']}")
            st.markdown(f"**Outcome:** {cs['outcome']}")
            if cs.get("url"):
                st.markdown(f"[Source link]({cs['url']})")

with t3:
    st.markdown("### LangChain BM25 RAG — guideline retrieval")
    c1, c2 = st.columns(2)
    with c1:
        diag = st.selectbox("Diagnosis", [
            "Urinary Tract Infection", "Community-Acquired Pneumonia", "Sepsis (unknown source)",
            "Skin & Soft Tissue Infection", "Hospital-Acquired Pneumonia",
        ])
    with c2:
        pat = st.selectbox("Pathogen", ["E. coli", "MRSA", "ESBL", "Klebsiella pneumoniae", "Unknown"])
    if st.button("Retrieve evidence", type="primary"):
        result = retrieve_clinical_evidence(diag, pat)
        st.markdown(f"**Query:** `{result['query']}` · **Method:** {result['retrieval_method']}")
        st.markdown("#### Guideline chunks")
        for e in result["evidence_chunks"]:
            st.markdown(f"**{e['title']}** ({e['type']})")
            st.info(e["excerpt"])
            if e.get("url"):
                st.caption(e["url"])
        st.markdown("#### Related case studies")
        for cs in result["related_case_studies"]:
            st.markdown(f"- **{cs['title']}** — {cs['clinical_lesson']}")

with t4:
    st.markdown("### Upload hospital antibiogram (WHONET / microbiology lab JSON)")
    st.markdown("""
**From your hospital microbiology department:**
1. Request **de-identified annual antibiogram** (organism × drug × % susceptible / % resistant)
2. Export from **WHONET**, BacLink, or Excel → JSON (template below)
3. Upload here → Clinician Console uses **your institution's data** instead of the reference dataset
    """)
    template = {
        "meta": {
            "dataset_id": "HOSPITAL-2025",
            "title": "Your Hospital — Institution Antibiogram",
            "region": "City, Country",
            "sources": ["Microbiology lab WHONET export 2024"],
            "citation": "Institutional data — used with hospital permission",
        },
        "organisms": {
            "e. coli": {
                "UTI": {
                    "nitrofurantoin": {"susceptibility_pct": 90, "resistance_pct": 10},
                    "ciprofloxacin": {"susceptibility_pct": 25, "resistance_pct": 75},
                }
            }
        },
    }
    st.code(json.dumps(template, indent=2), language="json")
    upload = st.text_area("Paste hospital antibiogram JSON", height=200)
    if st.button("Save hospital antibiogram"):
        try:
            payload = json.loads(upload)
            save_hospital_antibiogram(payload)
            st.success("Saved — Clinician Console now uses hospital antibiogram.")
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

st.divider()
m = get_live_dashboard_metrics()
st.caption(f"Live metrics: {m['total_recommendations']} cases logged · Antibiogram: {m['antibiogram_source']}")
