from __future__ import annotations

from datetime import datetime, timezone
import base64
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

from .domain import (
    AuthRequest,
    AuthResponse,
    EventRequest,
    StoredEvent,
    article_audience,
    article_category,
    article_matches_collection,
)
from .auth import UserStore
from .event_bus import build_event_bus
from .experiments import ExperimentService
from .experiment_stats import recommendation_experiment_report
from .recommender import RecommendationService
from .store import InMemoryStore
from .bandit import MultiArmedBandit
from .evaluations import compute_eval_metrics
try:
    from catalog_ui import product_png_bytes, product_svg
except ImportError:
    product_png_bytes = None
    product_svg = None
try:
    from event_store import append_event
except ImportError:
    append_event = None

app = FastAPI(title="FlipAttire Recommendation Platform", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
web_user_path = Path("D:/gt/web_user")
if web_user_path.exists():
    app.mount("/shop", StaticFiles(directory=web_user_path, html=True), name="shop")
recommendation_requests = Counter("hm_recommendation_requests_total", "Recommendation requests", ["surface", "variant"])
customer_events = Counter("hm_customer_events_total", "Customer events", ["event_type", "variant"])
catalog_articles = Gauge("hm_catalog_articles", "Articles loaded into serving memory")
articles_path = Path(os.getenv("HM_ARTICLES_PARQUET", "data/bronze/articles.parquet"))
popularity_path = Path(os.getenv("HM_POPULARITY_PARQUET", "models/artifacts/hm_baseline_v1.popularity.parquet"))
affinity_path = Path(os.getenv("HM_AFFINITY_PARQUET", "models/artifacts/hm_baseline_v1.customer_top_affinity.parquet"))
similarity_path = Path(os.getenv("HM_SIMILARITY_PARQUET", "models/artifacts/hm_spark_v1.item_similarity.parquet"))
# Do not load the 1.37M-customer history artifact in the online API by default.
# It is useful for offline training, but it can exhaust Windows memory while
# the storefront, Streamlit and Kafka services are running together.
history_env = os.getenv("HM_HISTORY_PARQUET", "")
history_path = Path(history_env) if history_env else None
if articles_path.exists() and popularity_path.exists():
    store = InMemoryStore.from_artifacts(articles_path, popularity_path, affinity_path if affinity_path.exists() else None, similarity_path if similarity_path.exists() else None, history_path if history_path and history_path.exists() else None)
else:
    store = InMemoryStore()
catalog_articles.set(len(store.articles))
# Restore per-user personalization from the durable JSONL event mirror
# (in-memory interactions would otherwise reset on every API restart).
if append_event is not None:
    try:
        from event_store import read_events as _read_events

        _restored = store.hydrate_from_log(_read_events(50000))
        if _restored:
            print(f"hydrated { _restored } customer interactions from event log")
    except Exception as exc:  # never block startup on log replay
        print(f"event hydration skipped: {exc}")
experiments = ExperimentService(store.experiment)
recommendations = RecommendationService(store, experiments)
event_bus = build_event_bus()
# Keep the assignable customer IDs backed by the compact profile index rather
# than copying more than a million IDs into another Python list.
_pool = store.customer_id_pool()
users = UserStore(_pool)
print(f"auth pool: {users.pool_size()} existing customers, {users.user_count()} registered logins")
bandit_router = MultiArmedBandit()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "flipattire-recommender"}


@app.get("/v1/recommendations")
def get_recommendations(
    customer_id: str,
    surface: str = "homepage",
    limit: int = Query(default=10, ge=1, le=100),
):
    result = recommendations.recommend(customer_id, surface, limit)
    recommendation_requests.labels(surface=surface, variant=result.variant).inc()
    return result


@app.get("/v1/evaluations")
def get_evaluations(k: int = Query(default=12, ge=1, le=50)):
    """Return offline & online recommendation evaluation metrics (MAP@12, NDCG@10, Precision, Recall, Coverage, Diversity)."""
    return compute_eval_metrics(store, store.events, k=k)


@app.get("/v1/analytics/stats")
def get_analytics_stats():
    """Return real-time analytics, CTR, conversion rate, and revenue statistics."""
    events = store.events
    impressions = sum(1 for e in events if e.event_type.value == "impression")
    clicks = sum(1 for e in events if e.event_type.value in {"click", "view"})
    carts = sum(1 for e in events if e.event_type.value == "add_to_cart")
    purchases = sum(1 for e in events if e.event_type.value == "purchase")
    users = len({e.customer_id for e in events})

    ctr = round((clicks / impressions) * 100, 2) if impressions else 0.0
    cvr = round((purchases / users) * 100, 2) if users else 0.0

    return {
        "total_events": len(events),
        "unique_users": users,
        "impressions": impressions,
        "clicks": clicks,
        "cart_additions": carts,
        "purchases": purchases,
        "overall_ctr_pct": ctr,
        "user_conversion_pct": cvr,
        "catalog_size": len(store.articles),
    }


@app.get("/v1/bandit/status")
def get_bandit_status():
    """Return process-local feedback counters for the experimental, non-routing bandit."""
    return bandit_router.get_stats()


@app.get("/v1/catalog")
def get_catalog(ids: list[str] | None = Query(default=None, max_length=100)):
    """Return article metadata needed by the browser storefront."""
    requested = ids or []
    result = []
    for article_id in requested:
        article = store.articles.get(article_id)
        if article:
            payload = article.model_dump()
            if product_png_bytes is not None:
                encoded = base64.b64encode(product_png_bytes(article)).decode("ascii")
                payload["image_data"] = f"data:image/png;base64,{encoded}"
            result.append(payload)
    return result


@app.get("/v1/catalog/{article_id}/image")
def get_catalog_image(article_id: str):
    article = store.articles.get(article_id)
    if not article or product_png_bytes is None:
        return Response(status_code=404)
    return Response(content=product_png_bytes(article), media_type="image/png")


@app.get("/v1/products")
def list_products(
    query: str | None = None,
    department: str | None = None,
    audience: str | None = Query(default=None, pattern="^(ALL|WOMEN|MEN|KIDS|BEAUTY|STUDIO|SALE)$"),
    category: str | None = Query(default=None, pattern="^(All|T-shirts & tops|Trousers & bottoms|Dresses|Jackets & layers|Shoes|Accessories)$"),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Paginated, catalog-taxonomy-filtered product browser (no image blobs)."""
    tokens = (query or "").strip().casefold().split()
    wanted = (department or "").strip().lower()
    wanted_audience = audience if audience and audience != "ALL" else None
    wanted_category = category if category and category != "All" else None
    # Single pass: skip `offset` matches, collect `limit` items.
    items: list[dict] = []
    skipped = 0
    for article in store.articles.values():
        if not article.available:
            continue
        if wanted and wanted not in article.department.lower():
            continue
        if wanted_audience in {"WOMEN", "MEN", "KIDS"} and article_audience(article) != wanted_audience:
            continue
        if wanted_audience in {"BEAUTY", "STUDIO", "SALE"} and not article_matches_collection(article, wanted_audience):
            continue
        if wanted_category and article_category(article) != wanted_category:
            continue
        searchable = f"{article.name} {article.product_type} {article.department} {article.colour_group}".casefold()
        if tokens and not all(token in searchable for token in tokens):
            continue
        if skipped < offset:
            skipped += 1
            continue
        if len(items) >= limit:
            break
        payload = article.model_dump()
        payload.pop("image_data", None)
        items.append(payload)
    return {"items": items, "offset": offset, "limit": limit}


@app.get("/v1/catalog/{article_id}/similar")
def get_similar(article_id: str, limit: int = Query(default=8, ge=1, le=24)):
    """Similar items for product detail pages (item-collaborative signal)."""
    from .domain import article_audience as _audience

    source = store.articles.get(article_id)
    source_aud = _audience(source) if source else ""
    candidates = store.similar_items(article_id)
    # Gender-aware: prefer same-audience (+ unisex "") companions so a MEN
    # purchase does not surface WOMEN items. Backfill if too few match.
    if source_aud in ("MEN", "WOMEN", "KIDS"):
        matching = [
            (sid, score)
            for sid, score in candidates
            if (a := store.articles.get(sid)) is not None and _audience(a) in (source_aud, "")
        ]
        if matching:
            rest = [(sid, score) for sid, score in candidates if sid not in {m[0] for m in matching}]
            candidates = matching + rest
    out = []
    for similar_id, score in candidates[:limit]:
        article = store.articles.get(similar_id)
        if not article:
            continue
        payload = article.model_dump()
        payload.pop("image_data", None)
        payload["similarity"] = score
        out.append(payload)
    return out


@app.get("/v1/customers/{customer_id}/events")
def get_customer_events(customer_id: str, limit: int = Query(default=100, ge=1, le=500)):
    """Order/activity history for the account page (most recent first)."""
    rows = [e for e in store.events if e.customer_id == customer_id]
    rows.sort(key=lambda e: e.event_time, reverse=True)
    return [e.model_dump(mode="json") for e in rows[:limit]]


@app.get("/v1/customers/{customer_id}/preview")
def get_customer_preview(customer_id: str, limit: int = Query(default=12, ge=1, le=50)):
    """Admin preview: what the engine would recommend this customer now, and why."""
    result = recommendations.recommend(customer_id, "preview", limit)
    items = []
    for rec in result.recommendations:
        article = store.articles.get(rec.article_id)
        payload = rec.model_dump()
        if article:
            meta = article.model_dump()
            meta.pop("image_data", None)
            payload["article"] = meta
        items.append(payload)
    departments = {k: int(v) for k, v in store.customer_departments(customer_id).most_common(5)}
    return {
        "customer_id": customer_id,
        "variant": result.variant,
        "experiment_id": result.experiment_id,
        "model_version": result.model_version,
        "top_departments": departments,
        "past_purchases": sum(1 for x in store.customer_interactions(customer_id) if x.event_type.value == "purchase"),
        "recommendations": items,
    }


@app.post("/v1/auth/register", response_model=AuthResponse, status_code=201)
def auth_register(request: AuthRequest) -> AuthResponse:
    try:
        customer_id, created = users.register(request.login_id, request.password)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc))
    return AuthResponse(login_id=request.login_id.strip().lower(), customer_id=customer_id, created=created)


@app.post("/v1/auth/login", response_model=AuthResponse)
def auth_login(request: AuthRequest) -> AuthResponse:
    from fastapi import HTTPException

    customer_id = users.login(request.login_id, request.password)
    if customer_id is None:
        raise HTTPException(status_code=401, detail="wrong login ID or password")
    return AuthResponse(login_id=request.login_id.strip().lower(), customer_id=customer_id, created=False)



@app.post("/v1/events", response_model=StoredEvent, status_code=201)
def record_event(request: EventRequest) -> StoredEvent:
    event = StoredEvent(
        event_id=str(uuid4()),
        event_time=datetime.now(timezone.utc),
        **request.model_dump(),
    )

    # Persist the event in the application's event store.
    store.save_event(event)

    # Update process-local bandit statistics using the same event timestamp
    # and product/customer identifiers used by experiment attribution.
    if event.variant:
        bandit_router.record_feedback(
            variant=event.variant,
            event_type=event.event_type.value,
            customer_id=event.customer_id,
            article_id=event.article_id,
            event_time=event.event_time,
        )

    # Preserve existing Prometheus event instrumentation.
    customer_events.labels(
        event_type=event.event_type.value,
        variant=event.variant or "unknown",
    ).inc()

    # Preserve the event bus and durable JSONL mirror.
    event_bus.publish("customer-events", event.model_dump())

    if append_event:
        append_event(event.model_dump(mode="json"))

    return event


@app.get("/v1/experiments/{experiment_id}/report")
def experiment_report(experiment_id: str):
    return recommendation_experiment_report(store.events, experiment_id)


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
