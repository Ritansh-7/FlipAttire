from __future__ import annotations

import runtime_env
import streamlit as st

from catalog_ui import category_image_path, clean_title, family, product_image_path
from hm_recommender.domain import Recommendation
from ui_data import get_runtime


st.set_page_config(page_title="FlipAttire style lab", page_icon=":material/checkroom:", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.stApp { background: #faf9f6; }
[data-testid="stSidebar"] { background: #1d241f; }
[data-testid="stSidebar"] * { color: #f7f4ec !important; }
.brand { font-size: 1.7rem; font-weight: 800; letter-spacing: -.06em; color: #1d241f; }
.eyebrow { text-transform: uppercase; letter-spacing: .14em; font-size: .72rem; color: #7d847b; font-weight: 700; }
.hero { padding: 2.6rem 3rem; border-radius: 26px; background: linear-gradient(115deg,#1e2720 0%,#566651 72%,#c9b39a 150%); color: white; margin: .5rem 0 1.4rem; }
.hero h1 { font-size: clamp(2.2rem,5vw,4.6rem); line-height: .95; letter-spacing: -.07em; margin: .25rem 0 .8rem; max-width: 650px; }
.hero p { color: #e9eee3; max-width: 560px; font-size: 1.02rem; }
.pill-note { color:#6c736a; font-size:.82rem; }
.product-meta h4 { margin:.55rem 0 .15rem; color:#1d241f; font-size:.96rem; }
.product-meta p { margin:0; color:#777d75; font-size:.78rem; }
div[data-testid="stMetric"] { background:#fff; border:1px solid #e9e5dc; border-radius:15px; padding:.8rem; }
</style>""", unsafe_allow_html=True)

runtime = get_runtime()
with st.sidebar:
    st.markdown("## FlipAttire style lab")
    st.caption("Personal discovery · powered by H&M-format catalog data")
    customer_id = st.text_input("Customer ID", key="customer_id", help="Paste a customer ID from customers.csv.")
    st.divider()
    st.markdown("**Your shopping mode**")
    surface = st.selectbox("Recommendation surface", ["homepage", "product_page", "checkout"], key="surface")
    st.caption("Every impression and action is assigned to the same experiment variant for this customer.")
    st.divider()
    st.page_link("http://localhost:8502", label="Open admin control room", icon=":material/monitoring:")

st.markdown('<div class="brand">FlipAttire / style lab</div>', unsafe_allow_html=True)
st.markdown('<div class="hero"><div class="eyebrow">Your edit · live personalization</div><h1>Find your next favourite.</h1><p>A calm, visual shopping experience built around your taste profile. Browse the edit, then tell the recommender what feels right.</p></div>', unsafe_allow_html=True)
st.image(
    category_image_path("New season"),
    caption="A fresh edit for the season",
    alt="New season fashion collection",
    width="stretch",
)

audience = st.segmented_control("Collection", ["All", "Ladies", "Men", "Kids"], default="All", key="audience") or "All"
categories = ["All", "T-shirts & tops", "Trousers & bottoms", "Dresses", "Jackets & layers", "Shoes", "Accessories"]
category = st.pills("Shop by category", categories, default="All", key="catalog_category") or "All"
search = st.text_input("Search the edit", placeholder="Try: black t-shirt, jeans, jacket", label_visibility="collapsed")

st.caption("Explore the edit")
category_visuals = st.columns(6, gap="small")
for visual_col, visual_category in zip(category_visuals, categories[1:]):
    with visual_col:
        st.image(
            category_image_path(visual_category),
            caption=visual_category.replace(" & ", " · "),
            alt=f"{visual_category} collection",
            width="stretch",
        )

result = runtime.recommendations.recommend(customer_id.strip(), surface, 32)
exposure_key = f"{result.request_id}:{customer_id}:{surface}"
if st.session_state.get("last_exposure") != exposure_key:
    runtime.record_impressions(customer_id.strip(), surface, result)
    st.session_state.last_exposure = exposure_key

with st.container(horizontal=True):
    st.metric("Your experiment", result.variant, border=True)
    st.metric("Style profile", "Learning", border=True)
    st.metric("Items in this edit", len(result.recommendations), border=True)


def audience_ok(article) -> bool:
    dept = str(article.department).lower()
    if audience == "All":
        return True
    if audience == "Ladies":
        return any(word in dept for word in ("ladies", "women", "girls"))
    if audience == "Men":
        return any(word in dept for word in ("men", "boys"))
    return "kids" in dept or "children" in dept or "baby" in dept


def category_ok(article) -> bool:
    return category == "All" or family(article.product_type) == category


def search_ok(article) -> bool:
    query = search.strip().lower()
    return not query or query in " ".join([article.name, article.product_type, article.department, article.colour_group]).lower()


items = []
for recommendation in result.recommendations:
    article = runtime.store.articles.get(recommendation.article_id)
    if article and audience_ok(article) and category_ok(article) and search_ok(article):
        items.append((recommendation, article))

# Keep the storefront useful even when the recommender's first 32 candidates
# are concentrated in another category: supplement with ranked catalog items.
seen_ids = {recommendation.article_id for recommendation, _ in items}
for article_id, score in runtime.store.popularity().most_common():
    if len(items) >= 16 or article_id in seen_ids:
        continue
    article = runtime.store.articles.get(article_id)
    if article and audience_ok(article) and category_ok(article) and search_ok(article):
        recommendation = Recommendation(article_id=article_id, position=len(items) + 1, score=float(score), source="catalog_popular")
        items.append((recommendation, article))
        seen_ids.add(article_id)

st.subheader("Picked for you", anchor=False)
st.markdown(f'<span class="pill-note">{result.model_version} · {result.variant} · recommendations adapt as you interact</span>', unsafe_allow_html=True)
if not items:
    st.info("No exact match in this edit yet. Try All or remove the search filter.")
else:
    for start in range(0, min(16, len(items)), 4):
        cols = st.columns(4, gap="medium")
        for col, (recommendation, article) in zip(cols, items[start:start + 4]):
            with col:
                with st.container(border=True):
                    st.image(
                        product_image_path(article),
                        alt=f"{clean_title(article)} product image",
                        width="stretch",
                    )
                    st.markdown(f'<div class="product-meta"><h4>{clean_title(article)}</h4><p>{article.product_type} · {article.colour_group} · {recommendation.source}</p></div>', unsafe_allow_html=True)
                    if st.button("View item", key=f"view-{result.request_id}-{article.article_id}", width="stretch", icon=":material/visibility:"):
                        st.session_state.selected_article = article.article_id
                        runtime.record_event("view", customer_id, article.article_id, surface, result)
                        st.toast("Added to your style trail")

selected_id = st.session_state.get("selected_article")
selected_article = runtime.store.articles.get(selected_id) if selected_id else None
if selected_article:
    st.space("small")
    with st.container(border=True):
        left, right = st.columns([1, 1.35], gap="large")
        with left:
            st.image(
                product_image_path(selected_article),
                alt=f"{clean_title(selected_article)} product image",
                width="stretch",
            )
        with right:
            st.markdown('<div class="eyebrow">Selected piece</div>', unsafe_allow_html=True)
            st.header(clean_title(selected_article), anchor=False)
            st.write(f"{selected_article.product_type} · {selected_article.department} · {selected_article.colour_group}")
            st.caption(selected_article.description[:260] if selected_article.description else "A considered piece selected from the catalog.")
            with st.container(horizontal=True):
                if st.button("Add to bag", type="primary", icon=":material/shopping_bag:"):
                    runtime.record_event("add_to_cart", customer_id, selected_id, surface, result)
                    st.success("Added to bag")
                if st.button("I like this", icon=":material/favorite:"):
                    runtime.record_event("click", customer_id, selected_id, surface, result)
                    st.toast("Your style profile got the signal")
                if st.button("Purchase", icon=":material/local_mall:"):
                    runtime.record_event("purchase", customer_id, selected_id, surface, result)
                    st.success("Purchase event recorded for the experiment")

st.subheader("Keep exploring", anchor=False)
with st.container(horizontal=True):
    st.caption("New in")
    st.caption("Everyday essentials")
    st.caption("Occasion edit")
    st.caption("Sport & movement")
