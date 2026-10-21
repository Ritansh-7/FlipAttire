from __future__ import annotations

import runtime_env
import socket
import urllib.parse
import urllib.request
from pathlib import Path

import streamlit as st

from event_store import read_events
from ui_data import get_runtime


st.set_page_config(page_title="FlipAttire control room", page_icon=":material/monitoring:", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.stApp { background:#f4f6f8; color:#14202b; }
.stApp [data-testid="stMain"] h1, .stApp [data-testid="stMain"] h2, .stApp [data-testid="stMain"] h3, .stApp [data-testid="stMain"] h4, .stApp [data-testid="stMain"] p, .stApp [data-testid="stMain"] label, .stApp [data-testid="stMain"] [data-testid="stMarkdownContainer"], .stApp [data-testid="stMain"] [data-testid="stCaptionContainer"], .stApp [data-testid="stMain"] [data-baseweb="tab"] { color:#14202b !important; }
.stApp [data-testid="stMain"] [data-baseweb="tab-list"] { background:#f4f6f8; }
.stApp [data-testid="stMain"] [data-baseweb="tab-highlight"] { background:#e53935; }
.stApp [data-testid="stMain"] [data-testid="stTextInput"] input { color:#14202b !important; background:#fff; }
[data-testid="stSidebar"] { background:#14202b; }
[data-testid="stSidebar"] * { color:#edf2f7 !important; }
.ops-hero { padding:1.8rem 2.2rem; border-radius:20px; background:linear-gradient(120deg,#14202b,#2d5364); color:#fff; margin:.5rem 0 1.2rem; }
.ops-hero h1 { margin:0; letter-spacing:-.06em; font-size:2.7rem; }
.ops-hero p { color:#c9d8e0; margin:.35rem 0 0; }
div[data-testid="stMetric"] { background:#fff; border:1px solid #e2e8ed; border-radius:14px; padding:.75rem; }
</style>""", unsafe_allow_html=True)

runtime = get_runtime()
with st.sidebar:
    st.markdown("## FlipAttire control room")
    st.caption("Spotify-inspired experimentation operations")
    auto = st.toggle("Live refresh", value=True)
    st.caption("Refresh interval: 5 seconds")
    st.divider()
    st.link_button("Kafka UI", "http://localhost:8080", width="stretch", icon=":material/topic:")
    st.link_button("Prometheus", "http://localhost:9090", width="stretch", icon=":material/query_stats:")
    st.link_button("Grafana", "http://localhost:3000", width="stretch", icon=":material/monitoring:")
    st.caption("All dashboards use D:/gt data and native services.")


def probe(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            return response.status < 500
    except Exception:
        return False


def tcp(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def live_state():
    events = read_events(10000)
    return events


def dashboard():
    events = live_state()
    impressions = sum(1 for event in events if event.get("event_type") == "impression")
    clicks = sum(1 for event in events if event.get("event_type") == "click")
    purchases = sum(1 for event in events if event.get("event_type") == "purchase")
    st.markdown('<div class="ops-hero"><div class="eyebrow">FlipAttire recommendation platform</div><h1>Control room</h1><p>Every click, model signal and experiment decision in one live view.</p></div>', unsafe_allow_html=True)
    with st.container(horizontal=True):
        st.metric("Live events", f"{len(events):,}", border=True)
        st.metric("Impressions", f"{impressions:,}", border=True)
        st.metric("CTR", f"{clicks / impressions * 100:.2f}%" if impressions else "0.00%", border=True)
        st.metric("Purchases", f"{purchases:,}", border=True)
    st.caption("Top-line CTR is raw clicks ÷ impressions in the local event log; it is not recommendation-attributed. Use the A/B tab for product-exposure-attributed rates.")

    st.subheader("Platform health", anchor=False)
    services = [
        {"Service": "FastAPI recommender", "Status": "Healthy" if probe("http://127.0.0.1:8000/health") else "Down", "Endpoint": ":8000"},
        {"Service": "Prometheus", "Status": "Healthy" if probe("http://127.0.0.1:9090/-/ready") else "Down", "Endpoint": ":9090"},
        {"Service": "Grafana", "Status": "Healthy" if probe("http://127.0.0.1:3000/api/health") else "Down", "Endpoint": ":3000"},
        {"Service": "Kafka broker", "Status": "Healthy" if tcp("127.0.0.1", 9092) else "Down", "Endpoint": ":9092"},
        {"Service": "Kafka UI", "Status": "Healthy" if probe("http://127.0.0.1:8080") else "Down", "Endpoint": ":8080"},
        {"Service": "PySpark artifacts", "Status": "Ready" if Path("models/artifacts/hm_spark_v1.json").exists() else "Missing", "Endpoint": "D:/gt/models/artifacts"},
    ]
    st.dataframe(services, hide_index=True, width="stretch", alt="Live FlipAttire platform service health")

    ab, rec, users, mlops, stream, quality = st.tabs(["A/B testing", "Recommendation evals", "User analytics", "MLOps & models", "Kafka event stream", "Data quality"])
    with ab:
        st.subheader("Fixed-split A/B experiment")
        st.caption("Purchase conversion is attributed to the same customer and product after an impression, for up to 7 days.")
        try:
            import json as _json
            with urllib.request.urlopen(
                "http://127.0.0.1:8000/v1/experiments/homepage_recommender_002/report", timeout=2
            ) as _res:
                experiment_data = _json.loads(_res.read().decode("utf-8"))
            rows = [
                {
                    "Variant": metric["variant"],
                    "Exposed customers": metric["exposed_users"],
                    "Impression events": metric["impression_events"],
                    "Product-view/customer": f"{metric['product_view_rate'] * 100:.2f}%",
                    "Click-through/customer": f"{metric['click_through_rate'] * 100:.2f}%",
                    "Add-to-cart/customer": f"{metric['add_to_cart_rate'] * 100:.2f}%",
                    "Purchase conversion": f"{metric['conversion_rate'] * 100:.2f}%",
                    "Purchasing customers": metric["converters"],
                }
                for metric in experiment_data.get("variants", [])
            ]
            if rows:
                st.dataframe(rows, hide_index=True, width="stretch", alt="Attributed A/B experiment metrics")
            else:
                st.info("No attributed recommendation exposures have been recorded for this experiment yet.")
            if experiment_data.get("customers_exposed_to_multiple_variants", 0):
                st.warning(
                    f"{experiment_data['customers_exposed_to_multiple_variants']} customers were exposed to multiple variants."
                )
            comparison = experiment_data.get("treatment_vs_control")
            if comparison:
                p_value = comparison.get("p_value")
                lift = comparison.get("absolute_lift")
                lift_text = f"{lift:.2%}" if lift is not None else "not available"
                if comparison.get("reason"):
                    test_text = comparison["reason"]
                elif p_value is not None:
                    test_text = f"exploratory z-test p-value: {p_value:.4g}"
                else:
                    test_text = "sample too small for the two-proportion z-test"
                st.caption(
                    f"Treatment-control conversion lift: {lift_text}; "
                    f"single-variant analysis: {comparison.get('control_exposed_users', 0)} control / "
                    f"{comparison.get('treatment_exposed_users', 0)} treatment customers; "
                    f"excluded cross-variant customers: {comparison.get('excluded_cross_variant_customers', 0)}; "
                    f"{test_text}."
                )
        except Exception as exc:
            st.caption(f"Experiment report unavailable: {exc}")
        
        # Feedback counters are diagnostic only; the recommender uses fixed hash assignment.
        try:
            import json as _json
            with urllib.request.urlopen("http://127.0.0.1:8000/v1/bandit/status", timeout=2) as _res:
                bandit_data = _json.loads(_res.read().decode("utf-8"))
            st.subheader("Bandit feedback (diagnostic only; not used for routing)")
            bandit_rows = [{"Arm": k, "Observed impression share": f"{v['traffic_share']}%", "Impressions": v['impressions'], "Views": v['views'], "Clicks": v['clicks'], "Carts": v['carts'], "Purchases": v['purchases'], "CTR": f"{v['ctr']}%", "Purchase / impression": f"{v['cvr']}%"} for k, v in bandit_data.items()]
            st.dataframe(bandit_rows, hide_index=True, width="stretch", alt="Bandit routing status")
        except Exception:
            st.caption("Bandit feedback counters are available when FastAPI is online; variant assignment is currently deterministic.")

    with rec:
        st.subheader("Recommendation Model Evaluations & Quality")
        eval_rows = [
            {"Evaluation": "Candidate ranking", "Value": "Popularity + department/colour affinity + item similarity", "Status": "Implemented"},
            {"Evaluation": "Diversity policy", "Value": "Max 3 / department", "Status": "Live"},
            {"Evaluation": "Variant assignment", "Value": "Stable customer hash, fixed split", "Status": "Live"},
        ]
        try:
            import json as _json
            with urllib.request.urlopen("http://127.0.0.1:8000/v1/evaluations", timeout=2) as _res:
                eval_data = _json.loads(_res.read().decode("utf-8"))
            eval_rows.append({
                "Evaluation": "Offline ranking metrics",
                "Value": eval_data.get("reason", "Not available"),
                "Status": "Not evaluated" if not eval_data.get("available") else "Available",
            })
        except Exception as exc:
            eval_rows.append({"Evaluation": "Offline ranking metrics", "Value": str(exc), "Status": "Unavailable"})
        st.dataframe(eval_rows, hide_index=True, width="stretch", alt="Recommendation evaluation status")
        st.code("Spark batch → Parquet artifacts → recommendation API\nAPI events → JSONL/Kafka → attributed experiment report\nPrometheus/Grafana → service metrics", language="text")


        st.subheader("What should we recommend? (per-customer preview)")
        st.caption("Paste any customer ID — the admin asks the live API what that shopper would see right now, and why.")
        preview_id = st.text_input("Preview customer ID", value="", placeholder="Paste a customer ID from the user app", key="preview_customer")
        if preview_id.strip():
            import json as _json
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:8000/v1/customers/{urllib.parse.quote(preview_id.strip())}/preview?limit=12", timeout=5) as response:
                    preview = _json.loads(response.read().decode("utf-8"))
                st.write(f"Variant **{preview.get('variant')}** · experiment `{preview.get('experiment_id')}` · past purchases **{preview.get('past_purchases', 0)}**")
                top = preview.get("top_departments") or {}
                if top:
                    st.write("Top departments: " + ", ".join(f"{dept} ({count})" for dept, count in top.items()))
                else:
                    st.caption("No taste signal yet — both variants start from the popularity baseline for a new shopper.")
                rows = []
                for rec in preview.get("recommendations", []):
                    article = rec.get("article") or {}
                    rows.append({
                        "Pos": rec.get("position"),
                        "Article": rec.get("article_id"),
                        "Name": article.get("name", "")[:40],
                        "Department": article.get("department", ""),
                        "Why (source)": rec.get("source"),
                        "Score": f"{float(rec.get('score', 0)):.1f}",
                    })
                st.dataframe(rows, hide_index=True, width="stretch", alt="Per-customer recommendation preview")
            except Exception as exc:
                st.warning(f"Preview unavailable: {exc}")
    with users:
        st.subheader("Customer timeline")
        selected_user = st.text_input("Search customer ID", value="", placeholder="Paste a customer ID from the user app")
        user_events = [event for event in events if not selected_user or str(event.get("customer_id", "")).startswith(selected_user)]
        if selected_user and not user_events:
            st.info("No event found for this customer yet.")
        else:
            user_rows = [{"Time": e.get("event_time", "")[:19], "Event": e.get("event_type"), "Article": e.get("article_id", ""), "Variant": e.get("variant", ""), "Surface": e.get("surface", "")} for e in reversed(user_events[-100:])]
            st.dataframe(user_rows, hide_index=True, width="stretch", alt="Customer event timeline")
            st.caption(f"Events visible: {len(user_events):,} · assignments are customer-stable.")
    with mlops:
        st.subheader("Model registry and PySpark")
        model_rows = []
        for artifact in sorted(Path("models/artifacts").glob("*.json")):
            try:
                import json
                payload = json.loads(artifact.read_text(encoding="utf-8"))
                model_rows.append({"Artifact": artifact.name, "Version": payload.get("model_version", artifact.stem), "Status": "Local snapshot", "Location": "D:/gt/models/artifacts"})
            except (OSError, ValueError):
                continue
        st.dataframe(model_rows, hide_index=True, width="stretch", alt="Recommendation model registry")
        st.dataframe([
            {"Pipeline": "PySpark ingestion", "Status": "Ready" if Path("data/bronze/transactions").exists() else "Pending", "Output": "D:/gt/data/bronze"},
            {"Pipeline": "PySpark training", "Status": "Ready" if Path("models/artifacts/hm_spark_v1.json").exists() else "Pending", "Output": "D:/gt/models/artifacts"},
            {"Pipeline": "Offline evaluation", "Status": "Run on demand", "Output": "spark_evaluate.py reports the global-popularity baseline"},
        ], hide_index=True, width="stretch", alt="PySpark pipeline status")
    with stream:
        st.subheader("customer-events")
        rows = [{"Time": e.get("event_time", "")[:19], "Event": e.get("event_type"), "Customer": e.get("customer_id", "")[:14], "Article": e.get("article_id", ""), "Variant": e.get("variant", ""), "Surface": e.get("surface", "")} for e in reversed(events[-100:])]
        st.dataframe(rows, hide_index=True, width="stretch", height=430, alt="Kafka customer events mirrored from the live stream")
    with quality:
        st.subheader("Event data quality")
        event_ids = [event.get("event_id") for event in events if event.get("event_id")]
        missing_user = sum(not event.get("customer_id") for event in events)
        missing_article = sum(not event.get("article_id") for event in events)
        duplicates = len(event_ids) - len(set(event_ids))
        st.dataframe([
            {"Check": "Total events", "Value": str(len(events)), "Status": "OK"},
            {"Check": "Missing customer IDs", "Value": str(missing_user), "Status": "OK" if not missing_user else "Review"},
            {"Check": "Missing article IDs", "Value": str(missing_article), "Status": "OK" if not missing_article else "Review"},
            {"Check": "Duplicate event IDs", "Value": str(duplicates), "Status": "OK" if not duplicates else "Review"},
            {"Check": "Event sinks", "Value": "JSONL mirror; Kafka optional", "Status": "Configured"},
        ], hide_index=True, width="stretch", alt="Customer event data quality checks")


if auto:
    @st.fragment(run_every="5s")
    def live_dashboard():
        dashboard()
    live_dashboard()
else:
    dashboard()
