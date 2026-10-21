from __future__ import annotations

import os
import math
from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

from .domain import Recommendation, RecommendationResponse, article_audience
from .experiments import ExperimentService
from .store import InMemoryStore


def _dominant_audience(store: InMemoryStore, customer_id: str) -> str | None:
    """Infer MEN/WOMEN/KIDS from customer's own history (majority vote)."""
    from collections import Counter as _Counter

    votes: _Counter[str] = _Counter()
    for interaction in store.customer_interactions(customer_id):
        article = store.articles.get(interaction.article_id)
        if not article:
            continue
        audience = article_audience(article)
        if audience:
            votes[audience] += 1
    for article_id in store.customer_history(customer_id)[:20]:
        article = store.articles.get(article_id)
        if not article:
            continue
        audience = article_audience(article)
        if audience:
            votes[audience] += 1
    if not votes:
        return None
    return votes.most_common(1)[0][0]


class RecommendationService:
    def __init__(self, store: InMemoryStore, experiments: ExperimentService, model_version: str | None = None) -> None:
        self.store = store
        self.experiments = experiments
        self.model_version = model_version or os.getenv("HM_MODEL_VERSION", "hybrid_v2")

    def recommend(self, customer_id: str, surface: str, limit: int) -> RecommendationResponse:
        variant = self.experiments.assign(customer_id)
        interactions = self.store.customer_interactions(customer_id)
        purchased = {x.article_id for x in interactions if x.event_type.value == "purchase"}
        preferred_departments = self.store.customer_departments(customer_id)
        popularity = self.store.popularity()
        similarity_scores: Counter[str] = Counter()
        department_interest: Counter[str] = Counter()
        colour_interest: Counter[str] = Counter()
        seed_strength: Counter[str] = Counter()
        event_weights = {"view": 1.0, "click": 2.0, "add_to_cart": 4.0, "purchase": 6.0}
        now = datetime.now(timezone.utc)

        for interaction in interactions:
            weight = event_weights.get(interaction.event_type.value, 0.0)
            if not weight or interaction.article_id not in self.store.articles:
                continue
            event_time = interaction.event_time
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
            age_days = max((now - event_time.astimezone(timezone.utc)).total_seconds(), 0.0) / 86_400
            strength = weight * math.exp(-math.log(2) * age_days / 30)
            article = self.store.articles[interaction.article_id]
            department_interest[article.department] += strength
            colour_interest[article.colour_group] += strength
            seed_strength[interaction.article_id] = max(seed_strength[interaction.article_id], strength)

        for position, article_id in enumerate(self.store.customer_history(customer_id)[:20]):
            seed_strength[article_id] = max(seed_strength[article_id], 1 / math.sqrt(position + 1))

        for article_id, strength in seed_strength.items():
            for similar_id, similarity in self.store.similar_items(article_id):
                similarity_scores[similar_id] += strength * similarity

        scored: list[tuple[float, str, str]] = []
        for article_id, article in self.store.articles.items():
            if not article.available or article_id in purchased:
                continue
            popularity_score = math.log1p(popularity.get(article_id, 0))
            score = popularity_score
            source = "popular"
            if variant == "hybrid_v2":
                signals = {
                    "personalized_affinity": 0.65 * math.log1p(preferred_departments.get(article.department, 0)),
                    "recent_department_interest": math.log1p(department_interest[article.department]),
                    "recent_colour_interest": 0.35 * math.log1p(colour_interest[article.colour_group]),
                    "item_collaborative": 0.75 * math.log1p(similarity_scores[article_id]),
                }
                strongest_signal, signal_score = max(signals.items(), key=lambda signal: signal[1])
                score += sum(signals.values())
                if signal_score > 0:
                    source = strongest_signal
            scored.append((score, article_id, source))

        # Gender-aware ordering: if we know the customer's dominant audience
        # (MEN/WOMEN/KIDS from past purchases), rank same-audience + unisex
        # ("") first, then backfill with the rest so the list never goes empty.
        dominant = _dominant_audience(self.store, customer_id)
        if dominant:
            def _aud(article_id: str) -> str:
                return article_audience(self.store.articles[article_id])

            scored.sort(key=lambda item: (-item[0], item[1]))
            preferred = [s for s in scored if _aud(s[1]) in (dominant, "")]
            others = [s for s in scored if _aud(s[1]) not in (dominant, "")]
            scored = preferred + others
        else:
            # Simple diversity policy: no more than three products per department.
            scored.sort(key=lambda item: (-item[0], item[1]))
        selected: list[Recommendation] = []
        department_counts: Counter[str] = Counter()
        for score, article_id, source in scored:
            department = self.store.articles[article_id].department
            if department_counts[department] >= 3:
                continue
            department_counts[department] += 1
            selected.append(Recommendation(article_id=article_id, position=len(selected) + 1, score=score, source=source))
            if len(selected) >= limit:
                break

        response = RecommendationResponse(
            request_id=str(uuid4()),
            customer_id=customer_id,
            surface=surface,
            experiment_id=self.store.experiment.experiment_id,
            variant=variant,
            model_version="popularity_v1" if variant == "control" else self.model_version,
            recommendations=selected,
        )
        return response
