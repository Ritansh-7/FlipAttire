import streamlit as st

from ui_data import get_runtime

st.header("My recommendations")
st.caption("Personalized fashion discovery powered by the H&M recommendation service.")

with st.container(border=True):
    customer_id = st.text_input("Customer ID", key="customer_id", help="Use a customer ID from customers.csv.")
    surface = st.selectbox("Recommendation surface", ["homepage", "product_page", "checkout"], key="user_surface")

runtime = get_runtime()
result = runtime.recommendations.recommend(customer_id, surface, 12)

with st.container(horizontal=True):
    st.metric("Experiment", result.experiment_id, border=True)
    st.metric("Variant", result.variant, border=True)
    st.metric("Model", result.model_version, border=True)

st.subheader("Recommended for you")
if not result.recommendations:
    st.info("No recommendations are available for this customer yet.")
else:
    rows = []
    for item in result.recommendations:
        article = runtime.store.articles.get(item.article_id)
        rows.append({
            "Position": item.position,
            "Article ID": item.article_id,
            "Product type": article.product_type if article else "unknown",
            "Department": article.department if article else "unknown",
            "Colour": article.colour_group if article else "unknown",
            "Source": item.source,
            "Score": round(item.score, 3),
        })
    st.dataframe(rows, hide_index=True, width="stretch", alt="Personalized H&M product recommendations")

with st.container(border=True):
    st.subheader("Feedback")
    article_id = st.selectbox("Article", [item.article_id for item in result.recommendations], key="feedback_article")
    event_type = st.selectbox("Action", ["click", "add_to_cart", "purchase"], key="feedback_action")
    if st.button("Record feedback", type="primary", icon=":material/send:"):
        runtime.record_event(event_type, customer_id, article_id, surface, result)
        st.success("Feedback recorded for the experiment.")

