import json
import os
from pathlib import Path

import streamlit as st

from ui_data import get_runtime

st.header("Admin console")
st.caption("Operational view of recommendation models and experimentation.")

runtime = get_runtime()
artifact_dir = Path("models/artifacts")
metadata_files = sorted(artifact_dir.glob("*.json"))

with st.container(horizontal=True):
    st.metric("Catalog articles", f"{len(runtime.store.articles):,}", border=True)
    st.metric("Experiment", runtime.store.experiment.experiment_id, border=True)
    st.metric("Events in session", f"{len(runtime.store.events):,}", border=True)

st.subheader("Model registry snapshot")
metadata = []
for path in metadata_files:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["artifact"] = path.name
        metadata.append(payload)
    except json.JSONDecodeError:
        continue
if metadata:
    st.dataframe(metadata, hide_index=True, width="stretch", alt="Recommendation model artifacts")
else:
    st.warning("No model metadata artifacts found.")

st.subheader("Experiment report")
report = runtime.experiment_report()
variants = report.get("variants", [])
if variants:
    st.dataframe(variants, hide_index=True, width="stretch", alt="Experiment variant metrics")
    if report.get("treatment_vs_control"):
        st.json(report["treatment_vs_control"])
else:
    st.info("No recommendation impressions have been recorded in this admin session yet.")

st.subheader("Release checklist")
checks = {
    "Spark ingestion artifact exists": Path("data/bronze/transactions").exists(),
    "Spark model metadata exists": Path("models/artifacts/hm_spark_v1.json").exists(),
    "Item similarity artifact exists": Path("models/artifacts/hm_spark_v1.item_similarity.parquet").exists(),
    "API event bus configured": bool(os.getenv("KAFKA_BOOTSTRAP_SERVERS")),
}
st.dataframe([{"Check": key, "Status": "ready" if value else "pending"} for key, value in checks.items()], hide_index=True, width="stretch", alt="Production release readiness checks")

