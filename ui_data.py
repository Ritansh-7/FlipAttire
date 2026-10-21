from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st

from hm_recommender.domain import EventType, StoredEvent
from hm_recommender.experiment_stats import recommendation_experiment_report
from hm_recommender.experiments import ExperimentService
from hm_recommender.recommender import RecommendationService
from hm_recommender.store import InMemoryStore
from hm_recommender.event_bus import build_event_bus
from event_store import append_event


@st.cache_resource
def get_runtime():
    history_path = Path(os.getenv("HM_HISTORY_PARQUET", "models/artifacts/hm_spark_v1.customer_recent_items.parquet")) if os.getenv("HM_UI_LOAD_HISTORY", "0") == "1" else None
    store = InMemoryStore.from_artifacts(
        Path(os.getenv("HM_ARTICLES_PARQUET", "data/bronze/articles.parquet")),
        Path(os.getenv("HM_POPULARITY_PARQUET", "models/artifacts/hm_baseline_v1.popularity.parquet")),
        Path(os.getenv("HM_AFFINITY_PARQUET", "models/artifacts/hm_baseline_v1.customer_top_affinity.parquet")),
        Path(os.getenv("HM_SIMILARITY_PARQUET", "models/artifacts/hm_spark_v1.item_similarity.parquet")),
        history_path,
    )
    event_bus = build_event_bus()
    service = RecommendationService(store, ExperimentService(store.experiment))

    class Runtime:
        pass

    runtime = Runtime()
    runtime.recommendations = service
    runtime.store = store

    def record_event(event_type, customer_id, article_id, surface, result):
        event = StoredEvent(
                event_id=str(uuid4()), event_time=datetime.now(timezone.utc), event_type=EventType(event_type),
                customer_id=customer_id, article_id=article_id, surface=surface,
                request_id=result.request_id, experiment_id=result.experiment_id, variant=result.variant,
        )
        store.save_event(event)
        append_event(event.model_dump(mode="json"))
        event_bus.publish("customer-events", event.model_dump(mode="json"))

    def record_impressions(customer_id, surface, result):
        for item in result.recommendations:
            record_event("impression", customer_id, item.article_id, surface, result)

    def experiment_report():
        return recommendation_experiment_report(store.events, store.experiment.experiment_id)

    runtime.record_event = record_event
    runtime.record_impressions = record_impressions
    runtime.experiment_report = experiment_report
    return runtime

